"""
Envío de notificaciones por correo a partir de las plantillas editables.

Uso desde otros módulos (dentro o fuera de una transacción):

    from notificaciones.services import notificar
    notificar(socio, "RESERVA_CONFIRMADA", detalle="Tenis, 20/10 09:00-10:00", reserva=reserva)

La notificación se guarda en el historial como PENDIENTE y el correo se envía
cuando la transacción hace commit; si la operación se revierte, no se envía
nada ni queda registro.
"""
import logging

from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Notificacion, PlantillaNotificacion

logger = logging.getLogger(__name__)


def _correo(socio):
    # Acepta socios.Socio (campo correo) o accounts.User (campo email).
    return getattr(socio, "correo", None) or socio.email


def notificar(socio, tipo, detalle="", reserva=None, **valores):
    """Registra una notificación del `tipo` indicado y programa su envío."""
    plantilla = PlantillaNotificacion.objects.get(pk=tipo)
    asunto, cuerpo = plantilla.renderizar(nombre=socio.nombre_completo, detalle=detalle, **valores)
    notificacion = Notificacion.objects.create(
        socio_id=socio.pk, tipo_id=tipo, correo_destino=_correo(socio),
        asunto=asunto[:200], cuerpo=cuerpo, reserva=reserva)
    transaction.on_commit(lambda: enviar(notificacion.pk))
    return notificacion


def enviar(id_notificacion):
    """Envía una notificación pendiente y registra el resultado (ENVIADA/FALLIDA)."""
    notificacion = Notificacion.objects.get(pk=id_notificacion)
    try:
        send_mail(notificacion.asunto, notificacion.cuerpo, None, [notificacion.correo_destino])
    except Exception:  # El fallo de correo no debe romper la operación del socio.
        logger.exception("No se pudo enviar la notificación %s", id_notificacion)
        notificacion.estado_id = "FALLIDA"
        notificacion.save(update_fields=["estado"])
        return False
    notificacion.estado_id = "ENVIADA"
    notificacion.fecha_envio = timezone.now()
    notificacion.save(update_fields=["estado", "fecha_envio"])
    return True
