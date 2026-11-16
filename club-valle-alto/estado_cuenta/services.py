"""
Estados de cuenta, cuotas mensuales, pagos manuales y recordatorios.

- generar_estados(periodo): crea el estado de cuenta del mes y la cuota de
  membresía de cada socio con membresía activa en ese mes. Se puede repetir
  sin duplicar nada (comando `generar_estados_cuenta`, mensual).
- registrar_pago(...): administración registra la recepción de un pago que
  salda uno o varios cargos completos.
- procesar_recordatorios(): marca cargos vencidos y avisa por correo los
  vencidos y los que están por vencer (comando `procesar_cobros`, diario).
"""
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from memberships.models import Membership
from notificaciones.models import Notificacion
from notificaciones.services import notificar
from .models import Cargo, EstadoCuenta, Pago, PagoCargo

# Día del mes siguiente al periodo en que vence el pago.
DIA_LIMITE_PAGO = 10
# Días de anticipación para el recordatorio de pago por vencer.
DIAS_AVISO_PAGO = 3
TIPO_CUOTA = "CUOTA_MEMBRESIA"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


# --- Utilidades ---------------------------------------------------------

def nombre_periodo(periodo):
    return f"{MESES[periodo.month - 1]} {periodo.year}"


def siguiente_mes(periodo):
    return date(periodo.year + 1, 1, 1) if periodo.month == 12 else date(periodo.year, periodo.month + 1, 1)


def limite_pago(periodo):
    return siguiente_mes(periodo).replace(day=DIA_LIMITE_PAGO)


def colones(monto):
    return "₡" + f"{monto:,.0f}".replace(",", " ")


def estado_visible(cargo, hoy=None):
    """Un cargo pendiente con la fecha límite vencida se muestra como VENCIDO aunque el proceso diario no haya corrido."""
    hoy = hoy or timezone.localdate()
    if cargo.estado_id == "PENDIENTE" and cargo.fecha_limite_pago < hoy:
        return "VENCIDO"
    return cargo.estado_id


def estado_resumen(resumen, hoy=None):
    """Estado global de un periodo (fila de v_estado_cuenta_resumen)."""
    hoy = hoy or timezone.localdate()
    if resumen.pendiente + resumen.vencido == 0:
        return "PAGADO"
    if resumen.vencido or resumen.fecha_limite_pago < hoy:
        return "VENCIDO"
    return "PENDIENTE"


def obtener_estado_cuenta(socio_id, fecha):
    """Estado de cuenta del socio para el mes de `fecha`; lo crea si no existe."""
    periodo = fecha.replace(day=1)
    estado, _ = EstadoCuenta.objects.get_or_create(
        socio_id=socio_id, periodo=periodo, defaults={"fecha_limite_pago": limite_pago(periodo)})
    return estado


# --- Generación mensual -------------------------------------------------

def membresias_a_cobrar(periodo):
    fin = siguiente_mes(periodo) - timedelta(days=1)
    return (Membership.objects.filter(estado="ACTIVA", fecha_inscripcion__lte=fin, fecha_renovacion__gte=periodo,
                                      socio__estado=User.Status.ACTIVE)
            .select_related("socio", "tipo").order_by("socio_id"))


def generar_estados(periodo):
    """Devuelve cuántas cuotas nuevas se generaron. Cada socio se procesa en su propia transacción."""
    periodo = periodo.replace(day=1)
    generadas = 0
    for membresia in membresias_a_cobrar(periodo):
        with transaction.atomic():
            obtener_estado_cuenta(membresia.socio_id, periodo)
            # Bloquear el estado de cuenta evita cuotas duplicadas si se genera dos veces a la vez.
            estado = EstadoCuenta.objects.select_for_update().get(socio_id=membresia.socio_id, periodo=periodo)
            if not membresia.cuota or Cargo.objects.filter(socio_id=estado.socio_id, periodo=periodo, tipo_id=TIPO_CUOTA).exists():
                continue
            Cargo.objects.create(socio_id=estado.socio_id, periodo=periodo, tipo_id=TIPO_CUOTA,
                                 descripcion=f"Cuota {membresia.tipo.nombre} - {nombre_periodo(periodo)}"[:200],
                                 monto=membresia.cuota, fecha_limite_pago=estado.fecha_limite_pago)
            total = sum(Cargo.objects.filter(socio_id=estado.socio_id, periodo=periodo).values_list("monto", flat=True))
            notificar(membresia.socio, "NUEVO_ESTADO_CUENTA",
                      f"Periodo {nombre_periodo(periodo)}: total {colones(total)}, "
                      f"fecha límite {estado.fecha_limite_pago:%d/%m/%Y}")
            generadas += 1
    return generadas


# --- Pagos --------------------------------------------------------------

@transaction.atomic
def registrar_pago(socio_id, cargos, fecha_pago, referencia, admin):
    ids = [c.pk if hasattr(c, "pk") else int(c) for c in cargos]
    if not ids:
        raise ValidationError("Seleccione al menos un cargo.")
    if fecha_pago > timezone.localdate():
        raise ValidationError("La fecha de pago no puede ser futura.")
    bloqueados = list(Cargo.objects.select_for_update().filter(pk__in=ids, socio_id=socio_id).order_by("pk"))
    if len(bloqueados) != len(set(ids)):
        raise ValidationError("Algún cargo no existe o no pertenece al socio.")
    if any(c.estado_id == "PAGADO" for c in bloqueados):
        raise ValidationError("Algún cargo ya fue pagado. Actualice la página e intente de nuevo.")

    pago = Pago.objects.create(socio_id=socio_id, fecha_pago=fecha_pago, monto=sum(c.monto for c in bloqueados),
                               referencia=referencia.strip(), admin_id=admin.pk)
    momento = timezone.now() if fecha_pago == timezone.localdate() else \
        timezone.make_aware(datetime.combine(fecha_pago, time(12)), timezone.get_default_timezone())
    for cargo in bloqueados:
        cargo.estado_id, cargo.fecha_pago, cargo.admin_pago_id = "PAGADO", momento, admin.pk
        cargo.save(update_fields=["estado", "fecha_pago", "admin_pago"])
        PagoCargo.objects.create(pago=pago, cargo=cargo, monto=cargo.monto)
    return pago


# --- Recordatorios ------------------------------------------------------

def _avisar(cargos, tipo):
    por_socio = defaultdict(list)
    for cargo in cargos:
        por_socio[cargo.socio_id].append(cargo)
    for lista in por_socio.values():
        total = sum(c.monto for c in lista)
        limite = min(c.fecha_limite_pago for c in lista)
        notificar(lista[0].socio, tipo, f"{len(lista)} cargo(s) por {colones(total)} con fecha límite {limite:%d/%m/%Y}")
    return len(por_socio)


@transaction.atomic
def procesar_recordatorios(hoy=None):
    """Devuelve (socios avisados de vencimiento, socios avisados de pago por vencer)."""
    hoy = hoy or timezone.localdate()
    vencidos = list(Cargo.objects.select_for_update(of=("self",)).filter(estado_id="PENDIENTE", fecha_limite_pago__lt=hoy)
                    .select_related("socio"))
    Cargo.objects.filter(pk__in=[c.pk for c in vencidos]).update(estado_id="VENCIDO")
    avisados_vencidos = _avisar(vencidos, "PAGO_VENCIDO")

    por_vencer = Cargo.objects.filter(estado_id="PENDIENTE", fecha_limite_pago=hoy + timedelta(days=DIAS_AVISO_PAGO)) \
        .select_related("socio")
    # Si el proceso corre más de una vez el mismo día, no se repite el aviso.
    ya_avisados = set(Notificacion.objects.filter(tipo_id="PAGO_POR_VENCER", fecha_creacion__date=hoy)
                      .values_list("socio_id", flat=True))
    avisados_por_vencer = _avisar([c for c in por_vencer if c.socio_id not in ya_avisados], "PAGO_POR_VENCER")
    return avisados_vencidos, avisados_por_vencer
