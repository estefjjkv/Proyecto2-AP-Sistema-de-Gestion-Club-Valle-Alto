"""
Reglas de negocio de las reservas.

Flujo acordado:
  - El socio crea o modifica una reserva -> queda PENDIENTE (ocupa el horario).
  - Un administrador la confirma -> CONFIRMADA (correo RESERVA_CONFIRMADA).
  - Las reservas creadas por un administrador nacen CONFIRMADAS.
  - Cancelar libera el horario (correo RESERVA_CANCELADA).
  - El comando `finalizar_reservas` pasa a FINALIZADA las confirmadas que ya
    terminaron y cancela las pendientes que nunca se confirmaron.

Los servicios adicionales generan un único cargo SERVICIO_ADICIONAL por reserva
en el estado de cuenta del mes de la reserva. Si la reserva se cancela o se
quitan los servicios, el cargo pendiente se elimina; un cargo pagado no se toca.

La base de datos vuelve a validar todo (trigger y EXCLUDE). Aquí se valida
antes para dar mensajes claros, y los errores de la base se traducen.
"""
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from accounts.models import Administrator
from estado_cuenta.models import Cargo
from estado_cuenta.services import obtener_estado_cuenta
from instalaciones.models import BloqueoInstalacion, Instalacion
from instalaciones.services import VIGENTES, reservas_en_rango
from memberships.models import Membership
from notificaciones.services import notificar
from .models import Reserva, ReservaHistorial, ReservaServicio

TIPO_CARGO = "SERVICIO_ADICIONAL"


# --- Utilidades ---------------------------------------------------------

def _local(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora), timezone.get_default_timezone())


def es_admin(usuario):
    return isinstance(usuario, Administrator)


def describir(reserva):
    return (f"{reserva.instalacion.nombre}, {reserva.fecha:%d/%m/%Y} "
            f"de {reserva.hora_inicio:%H:%M} a {reserva.hora_fin:%H:%M}")


def ya_inicio(reserva):
    return _local(reserva.fecha, reserva.hora_inicio) <= timezone.now()


def puede_gestionar_socio(reserva):
    """El socio puede modificar o cancelar mientras la reserva no haya iniciado."""
    return reserva.estado_id in VIGENTES and not ya_inicio(reserva)


def registrar(reserva, accion, usuario, detalle=""):
    if usuario is None:
        tipo, cedula, nombre = ReservaHistorial.Actor.SISTEMA, "", ""
    else:
        tipo = ReservaHistorial.Actor.ADMIN if es_admin(usuario) else ReservaHistorial.Actor.SOCIO
        cedula, nombre = usuario.pk, usuario.nombre_completo
    ReservaHistorial.objects.create(reserva_id=reserva.pk, accion=accion, actor_tipo=tipo,
                                    actor_cedula=cedula, actor_nombre=nombre, detalle=detalle[:500])


def _guardar(reserva, **opciones):
    """Guarda traduciendo los rechazos del trigger y de la restricción EXCLUDE."""
    try:
        with transaction.atomic():
            reserva.save(**opciones)
    except IntegrityError as error:
        if getattr(error.__cause__, "sqlstate", None) == "23P01":
            raise ValidationError("El horario se traslapa con otra reserva. Elija otro horario.")
        raise
    except DatabaseError as error:
        diag = getattr(error.__cause__, "diag", None)
        mensaje = getattr(diag, "message_primary", None)
        if mensaje:
            raise ValidationError(mensaje)
        raise


# --- Validaciones -------------------------------------------------------

def validar_membresia(socio_id, fecha):
    membresia = Membership.objects.filter(socio_id=socio_id).first()
    if membresia is None or not membresia.vigente:
        raise ValidationError("El socio necesita una membresía activa y vigente para reservar.")
    if fecha > membresia.fecha_renovacion:
        raise ValidationError(f"La fecha debe estar dentro de la vigencia de la membresía "
                              f"(hasta el {membresia.fecha_renovacion:%d/%m/%Y}).")


def validar_horario(instalacion, fecha, hora_inicio, hora_fin, personas, excluir=None):
    if hora_fin <= hora_inicio:
        raise ValidationError("La hora de finalización debe ser posterior a la de inicio.")
    inicio, fin = _local(fecha, hora_inicio), _local(fecha, hora_fin)
    if inicio <= timezone.now():
        raise ValidationError("La reserva debe ser para un horario futuro.")
    if not instalacion.activa:
        raise ValidationError("La instalación no está disponible para reservas.")
    if hora_inicio < instalacion.hora_apertura or hora_fin > instalacion.hora_cierre:
        raise ValidationError(f"{instalacion.nombre} atiende de {instalacion.hora_apertura:%H:%M} "
                              f"a {instalacion.hora_cierre:%H:%M}.")
    if not 1 <= personas <= instalacion.aforo_maximo:
        raise ValidationError(f"El número de personas debe estar entre 1 y {instalacion.aforo_maximo}.")
    if BloqueoInstalacion.objects.filter(instalacion=instalacion, inicio__lt=fin, fin__gt=inicio).exists():
        raise ValidationError("La instalación está bloqueada en ese horario.")
    choques = reservas_en_rango(instalacion, inicio, fin)
    if excluir:
        choques = choques.exclude(pk=excluir)
    if choques.exists():
        raise ValidationError("El horario seleccionado se traslapa con otra reserva. Elija otro horario.")


def validar_servicios(instalacion, servicios, actuales=()):
    for servicio in servicios:
        if servicio.tipo_instalacion_id != instalacion.tipo_id:
            raise ValidationError(f"El servicio «{servicio.nombre}» no corresponde a {instalacion.nombre}.")
        if not servicio.activo and servicio.pk not in actuales:
            raise ValidationError(f"El servicio «{servicio.nombre}» ya no está disponible.")


# --- Servicios adicionales y cargo ---------------------------------------

def _cargo_pagado(reserva):
    return Cargo.objects.filter(reserva_id=reserva.pk, tipo_id=TIPO_CARGO, estado_id="PAGADO").exists()


def _sincronizar_servicios(reserva, servicios):
    actuales = set(reserva.servicios.values_list("servicio_id", flat=True))
    deseados = {s.pk: s for s in servicios}
    ReservaServicio.objects.filter(reserva_id=reserva.pk, servicio_id__in=actuales - deseados.keys()).delete()
    for codigo in deseados.keys() - actuales:  # precio congelado al momento de agregarlo
        ReservaServicio.objects.create(reserva_id=reserva.pk, servicio_id=codigo, cantidad=1,
                                       precio_unitario=deseados[codigo].precio)


def _sincronizar_cargo(reserva):
    pendiente = Cargo.objects.filter(reserva_id=reserva.pk, tipo_id=TIPO_CARGO).exclude(estado_id="PAGADO").first()
    if _cargo_pagado(reserva):
        return
    lineas = list(ReservaServicio.objects.filter(reserva_id=reserva.pk).select_related("servicio"))
    total = sum((linea.subtotal for linea in lineas), 0)
    if reserva.estado_id == "CANCELADA" or not total:
        if pendiente:
            pendiente.delete()
        return
    periodo = reserva.fecha.replace(day=1)
    if pendiente and pendiente.periodo != periodo:
        pendiente.delete()
        pendiente = None
    descripcion = (f"Servicios reserva #{reserva.pk} ({reserva.instalacion.nombre} {reserva.fecha:%d/%m}): "
                   + ", ".join(linea.servicio.nombre for linea in lineas))[:200]
    if pendiente:
        pendiente.monto, pendiente.descripcion = total, descripcion
        pendiente.save(update_fields=["monto", "descripcion"])
    else:
        estado = obtener_estado_cuenta(reserva.socio_id, reserva.fecha)
        Cargo.objects.create(socio_id=reserva.socio_id, periodo=periodo, tipo_id=TIPO_CARGO,
                             descripcion=descripcion, monto=total,
                             fecha_limite_pago=estado.fecha_limite_pago, reserva_id=reserva.pk)


# --- Operaciones --------------------------------------------------------

@transaction.atomic
def crear_reserva(data, usuario):
    """data: instalacion, fecha, hora_inicio, hora_fin, numero_personas, servicios y, si es admin, socio."""
    admin = es_admin(usuario)
    socio_id = data["socio"].pk if admin else usuario.pk
    # Bloquear la instalación serializa la reserva con bloqueos y cambios de horario.
    instalacion = Instalacion.objects.select_for_update().get(pk=data["instalacion"].pk)
    servicios = list(data.get("servicios") or [])
    validar_membresia(socio_id, data["fecha"])
    validar_horario(instalacion, data["fecha"], data["hora_inicio"], data["hora_fin"], data["numero_personas"])
    validar_servicios(instalacion, servicios)

    reserva = Reserva(socio_id=socio_id, instalacion=instalacion, fecha=data["fecha"],
                      hora_inicio=data["hora_inicio"], hora_fin=data["hora_fin"],
                      numero_personas=data["numero_personas"],
                      estado_id="CONFIRMADA" if admin else "PENDIENTE", admin_id=usuario.pk if admin else None)
    _guardar(reserva, force_insert=True)
    _sincronizar_servicios(reserva, servicios)
    _sincronizar_cargo(reserva)
    if admin:
        registrar(reserva, "CREADA", usuario, "Creada y confirmada por administración.")
        notificar(reserva.socio, "RESERVA_CONFIRMADA", describir(reserva), reserva=reserva)
    else:
        registrar(reserva, "CREADA", usuario, "Solicitud registrada por el socio.")
    return reserva


@transaction.atomic
def modificar_reserva(pk, data, usuario, confirmar=False):
    admin = es_admin(usuario)
    reserva = Reserva.objects.select_for_update().select_related("instalacion").get(pk=pk)
    if not admin and reserva.socio_id != usuario.pk:
        raise ValidationError("La reserva no le pertenece.")
    if reserva.estado_id not in VIGENTES:
        raise ValidationError("Solo se pueden modificar reservas pendientes o confirmadas.")
    if not admin and ya_inicio(reserva):
        raise ValidationError("La reserva ya inició; no se puede modificar.")
    if confirmar and not admin:
        raise ValidationError("Solo administración puede confirmar reservas.")

    instalacion = Instalacion.objects.select_for_update().get(pk=data["instalacion"].pk)
    servicios = list(data.get("servicios") or [])
    actuales = set(reserva.servicios.values_list("servicio_id", flat=True))
    nuevos = {
        "instalacion": instalacion.pk, "fecha": data["fecha"], "hora_inicio": data["hora_inicio"],
        "hora_fin": data["hora_fin"], "numero_personas": data["numero_personas"],
    }
    anteriores = {"instalacion": reserva.instalacion_id, "fecha": reserva.fecha, "hora_inicio": reserva.hora_inicio,
                  "hora_fin": reserva.hora_fin, "numero_personas": reserva.numero_personas}
    cambios = [campo for campo in nuevos if nuevos[campo] != anteriores[campo]]
    cambian_servicios = {s.pk for s in servicios} != actuales
    if not cambios and not cambian_servicios and not confirmar:
        return reserva

    if cambios:
        validar_membresia(reserva.socio_id, data["fecha"])
        validar_horario(instalacion, data["fecha"], data["hora_inicio"], data["hora_fin"],
                        data["numero_personas"], excluir=reserva.pk)
    validar_servicios(instalacion, servicios, actuales)
    if _cargo_pagado(reserva) and (cambian_servicios or data["fecha"].replace(day=1) != reserva.fecha.replace(day=1)):
        raise ValidationError("Los servicios de esta reserva ya fueron pagados: no se pueden cambiar los servicios ni el mes.")

    reserva.instalacion = instalacion
    for campo in ("fecha", "hora_inicio", "hora_fin", "numero_personas"):
        setattr(reserva, campo, data[campo])
    if admin:
        reserva.admin_id = usuario.pk
        if confirmar:
            reserva.estado_id = "CONFIRMADA"
    else:
        reserva.estado_id = "PENDIENTE"  # un cambio del socio requiere nueva confirmación
    _guardar(reserva)
    _sincronizar_servicios(reserva, servicios)
    _sincronizar_cargo(reserva)

    if cambios or cambian_servicios:
        etiquetas = {"instalacion": "instalación", "fecha": "fecha", "hora_inicio": "hora de inicio",
                     "hora_fin": "hora de finalización", "numero_personas": "personas"}
        detalle = ", ".join(etiquetas[c] for c in cambios) + (", servicios" if cambian_servicios else "")
        registrar(reserva, "MODIFICADA", usuario, "Cambios: " + detalle.lstrip(", ") + ".")
    if confirmar:
        registrar(reserva, "CONFIRMADA", usuario)
        notificar(reserva.socio, "RESERVA_CONFIRMADA", describir(reserva), reserva=reserva)
    elif admin:
        notificar(reserva.socio, "RESERVA_MODIFICADA", describir(reserva), reserva=reserva)
    return reserva


@transaction.atomic
def cancelar_reserva(pk, usuario, motivo=""):
    """usuario=None indica una cancelación automática del sistema."""
    reserva = Reserva.objects.select_for_update().select_related("instalacion", "socio").get(pk=pk)
    if usuario is not None and not es_admin(usuario):
        if reserva.socio_id != usuario.pk:
            raise ValidationError("La reserva no le pertenece.")
        if ya_inicio(reserva):
            raise ValidationError("La reserva ya inició; no se puede cancelar.")
    if reserva.estado_id not in VIGENTES:
        raise ValidationError("La reserva ya no está vigente.")
    reserva.estado_id = "CANCELADA"
    reserva.fecha_cancelacion = timezone.now()
    if es_admin(usuario):
        reserva.admin_id = usuario.pk
    _guardar(reserva)
    _sincronizar_cargo(reserva)
    registrar(reserva, "CANCELADA", usuario, motivo)
    detalle = describir(reserva) + (f". Motivo: {motivo}" if motivo else "")
    notificar(reserva.socio, "RESERVA_CANCELADA", detalle, reserva=reserva)
    return reserva


def finalizar_reservas(ahora=None):
    """Cierra las reservas cuyo horario ya pasó. Devuelve (finalizadas, canceladas)."""
    ahora = timezone.localtime(ahora or timezone.now())
    hoy, hora = ahora.date(), ahora.time()
    pasadas = Reserva.objects.filter(fecha__lt=hoy) | Reserva.objects.filter(fecha=hoy)
    finalizadas = canceladas = 0
    for reserva in pasadas.filter(estado_id="CONFIRMADA").order_by("pk"):
        if reserva.fecha == hoy and reserva.hora_fin > hora:
            continue
        with transaction.atomic():
            reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
            if reserva.estado_id == "CONFIRMADA":
                reserva.estado_id = "FINALIZADA"
                reserva.save(update_fields=["estado"])
                registrar(reserva, "FINALIZADA", None)
                finalizadas += 1
    for reserva in pasadas.filter(estado_id="PENDIENTE").order_by("pk"):
        if reserva.fecha == hoy and reserva.hora_inicio > hora:
            continue
        try:
            cancelar_reserva(reserva.pk, None, "No fue confirmada antes de su inicio.")
            canceladas += 1
        except ValidationError:
            pass  # cambió de estado mientras tanto
    return finalizadas, canceladas


# --- Consultas ----------------------------------------------------------

def disponibilidad(instalacion, fecha, excluir=None):
    """
    Franjas del día entre apertura y cierre: libre, pendiente, ocupado o bloqueado.
    Devuelve una lista de dicts {inicio, fin, estado, etiqueta} con horas "HH:MM".
    """
    if not instalacion.activa:
        return []
    apertura, cierre = _local(fecha, instalacion.hora_apertura), _local(fecha, instalacion.hora_cierre)
    eventos = []
    reservas = Reserva.objects.filter(instalacion=instalacion, fecha=fecha, estado_id__in=VIGENTES)
    if excluir:
        reservas = reservas.exclude(pk=excluir)
    for r in reservas:
        estado = "pendiente" if r.estado_id == "PENDIENTE" else "ocupado"
        eventos.append((_local(fecha, r.hora_inicio), _local(fecha, r.hora_fin), estado))
    for b in BloqueoInstalacion.objects.filter(instalacion=instalacion, inicio__lt=cierre, fin__gt=apertura).select_related("motivo"):
        eventos.append((max(b.inicio, apertura), min(b.fin, cierre), "bloqueado", str(b.motivo)))
    eventos.sort(key=lambda e: e[0])

    etiquetas = {"libre": "Disponible", "pendiente": "Solicitada", "ocupado": "Ocupado"}
    franjas, cursor = [], apertura
    for evento in eventos:
        inicio, fin, estado = evento[:3]
        if inicio > cursor:
            franjas.append((cursor, inicio, "libre", etiquetas["libre"]))
        franjas.append((max(inicio, cursor), fin, estado, evento[3] if len(evento) > 3 else etiquetas[estado]))
        cursor = max(cursor, fin)
    if cursor < cierre:
        franjas.append((cursor, cierre, "libre", etiquetas["libre"]))
    return [{"inicio": f"{timezone.localtime(i):%H:%M}", "fin": f"{timezone.localtime(f):%H:%M}",
             "estado": e, "etiqueta": t} for i, f, e, t in franjas if f > i]
