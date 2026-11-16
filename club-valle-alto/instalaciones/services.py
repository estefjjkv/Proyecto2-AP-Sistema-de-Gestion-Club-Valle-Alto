"""
Reglas de negocio de instalaciones, servicios adicionales y bloqueos.

Política acordada: si un cambio (bloqueo, desactivación, horario o aforo menor)
afecta reservas vigentes, se rechaza y se indica cuáles son; el administrador
las gestiona primero.

Concurrencia: estas operaciones bloquean la fila de la instalación con
SELECT ... FOR UPDATE. El servicio de reservas debe bloquear la misma fila
(al menos FOR SHARE) antes de insertar, para que una reserva y un bloqueo
simultáneos no se crucen.
"""
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BooleanField, Max, Q
from django.db.models.expressions import RawSQL
from django.utils import timezone

from reservas.models import Reserva
from .models import BloqueoInstalacion, Instalacion, VOcupacionFranja, VUsoInstalacion

VIGENTES = ("PENDIENTE", "CONFIRMADA")


def _naive(momento):
    """Hora local sin zona, igual que las columnas timestamp de la base."""
    if timezone.is_aware(momento):
        return timezone.make_naive(momento, timezone.get_default_timezone())
    return momento


def _describir(reservas, limite=5):
    reservas = list(reservas[:limite + 1])
    texto = ", ".join(f"#{r.pk} {r.fecha:%d/%m/%Y} {r.hora_inicio:%H:%M}-{r.hora_fin:%H:%M}" for r in reservas[:limite])
    return texto + (" y otras" if len(reservas) > limite else "")


def reservas_vigentes(instalacion):
    return Reserva.objects.filter(instalacion=instalacion, estado_id__in=VIGENTES).order_by("fecha", "hora_inicio")


def reservas_en_rango(instalacion, inicio, fin):
    """Reservas vigentes de la instalación que se traslapan con [inicio, fin)."""
    choca = RawSQL("rango && tsrange(%s, %s)", (_naive(inicio), _naive(fin)), output_field=BooleanField())
    return reservas_vigentes(instalacion).annotate(choca=choca).filter(choca=True)


@transaction.atomic
def guardar_instalacion(data, codigo=None):
    if codigo:
        instalacion = Instalacion.objects.select_for_update().get(pk=codigo)
    else:
        instalacion = Instalacion(codigo=data["codigo"])
    for campo in ("nombre", "tipo", "aforo_maximo", "hora_apertura", "hora_cierre", "activa"):
        setattr(instalacion, campo, data[campo])

    if codigo:
        futuras = reservas_vigentes(instalacion).filter(fecha__gte=timezone.localdate())
        if not instalacion.activa and futuras.exists():
            raise ValidationError("No se puede desactivar: tiene reservas vigentes (%s). Cancélelas o reprográmelas primero."
                                  % _describir(futuras))
        fuera = futuras.filter(Q(hora_inicio__lt=instalacion.hora_apertura) | Q(hora_fin__gt=instalacion.hora_cierre)
                               | Q(numero_personas__gt=instalacion.aforo_maximo))
        if fuera.exists():
            raise ValidationError("El nuevo horario o aforo deja fuera reservas vigentes (%s)." % _describir(fuera))

    instalacion.full_clean()
    instalacion.save(force_insert=not codigo, force_update=bool(codigo))
    return instalacion


@transaction.atomic
def crear_bloqueo(data, admin):
    instalacion = Instalacion.objects.select_for_update().get(pk=data["instalacion"].pk)
    inicio, fin = data["inicio"], data["fin"]
    conflictos = reservas_en_rango(instalacion, inicio, fin)
    if conflictos.exists():
        raise ValidationError("Hay reservas vigentes en ese horario (%s). Gestiónelas antes de bloquear."
                              % _describir(conflictos))
    if BloqueoInstalacion.objects.filter(instalacion=instalacion, inicio__lt=fin, fin__gt=inicio).exists():
        raise ValidationError("Ya existe un bloqueo de esta instalación que se traslapa con ese horario.")
    bloqueo = BloqueoInstalacion(instalacion=instalacion, inicio=inicio, fin=fin, motivo=data["motivo"],
                                 descripcion=data.get("descripcion") or None, admin_id=admin.pk)
    bloqueo.save(force_insert=True)  # La restricción EXCLUDE de la base respalda la validación anterior.
    return bloqueo


def bloqueo_actual(instalacion, momento=None):
    momento = momento or timezone.now()
    return instalacion.bloqueos.filter(inicio__lte=momento, fin__gt=momento).select_related("motivo").first()


def ocupacion(fecha, desde, hasta):
    """
    Ocupación de cada instalación activa en la franja [desde, hasta) del día.
    Las reservas vigentes de una instalación nunca se traslapan, así que la
    ocupación de la franja es la mayor cantidad de personas entre las reservas
    que la tocan.
    """
    maximos = dict(VOcupacionFranja.objects.filter(fecha=fecha, hora_inicio__lt=hasta, hora_fin__gt=desde)
                   .values("codigo_instalacion").annotate(personas=Max("numero_personas"))
                   .values_list("codigo_instalacion", "personas"))
    momento = timezone.make_aware(datetime.combine(fecha, desde), timezone.get_default_timezone())
    filas = []
    for instalacion in Instalacion.objects.filter(activa=True).order_by("nombre"):
        personas = maximos.get(instalacion.codigo, 0)
        filas.append({"instalacion": instalacion, "personas": personas,
                      "porcentaje": round(100 * personas / instalacion.aforo_maximo),
                      "bloqueo": bloqueo_actual(instalacion, momento)})
    return filas


def reporte_uso(periodo):
    """Uso de todas las instalaciones en el mes `periodo` (incluye las que no tuvieron reservas)."""
    uso = {u.codigo_instalacion: u for u in VUsoInstalacion.objects.filter(periodo=periodo)}
    filas = []
    for instalacion in Instalacion.objects.order_by("nombre"):
        u = uso.get(instalacion.codigo)
        filas.append({"instalacion": instalacion, "reservas": u.total_reservas if u else 0,
                      "horas": u.horas_reservadas if u else 0, "personas": u.total_personas if u else 0})
    filas.sort(key=lambda f: (-f["reservas"], f["instalacion"].nombre))
    tope = filas[0]["reservas"] if filas else 0
    for fila in filas:
        fila["ancho"] = round(100 * fila["reservas"] / tope) if tope else 0
    total = sum(f["reservas"] for f in filas)
    return {"filas": filas, "total": total,
            "mayor": filas[0]["instalacion"] if total else None,
            "menor": filas[-1]["instalacion"] if total else None}
