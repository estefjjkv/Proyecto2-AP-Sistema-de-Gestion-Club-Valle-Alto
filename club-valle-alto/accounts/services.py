import hashlib
import secrets
import logging
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from .models import User, Administrator, AccountEvent, RecoveryToken
logger = logging.getLogger(__name__)


def audit(user, actor, action, detail=""):
    AccountEvent.objects.create(target_kind="socio" if isinstance(user, User) else "administrador", target_id=user.pk,
        actor_id=actor.pk if actor else "", actor_kind=("administrador" if isinstance(actor,Administrator) else "socio") if actor else "", action=action, detail=detail)


def send_password_reset(email):
    token = secrets.token_urlsafe(32)
    digest = hashlib.sha256(token.encode()).hexdigest()
    with transaction.atomic():
        user = User.objects.select_for_update().filter(email__iexact=email, estado="ACTIVA").first()
        if user is None: return True
        # Mantener válidos los enlaces anteriores hasta usar uno; no denegar por reenvíos.
        RecoveryToken.objects.create(token_hash=digest, socio=user, fecha_expira=timezone.now()+timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT))
        address = settings.SITE_URL + reverse("usuarios:reset_confirm", args=[token])
        body = render_to_string("usuarios/reset_email.txt", {"user":user, "reset_url":address})
    try:
        send_mail("Restablecer contraseña · Club Valle Alto", body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:
        RecoveryToken.objects.filter(token_hash=digest).delete()
        logger.error("No se pudo enviar el correo; revise SMTP.")
        return False
    return True


def get_reset_user(raw):
    digest = hashlib.sha256(raw.encode()).hexdigest()
    token = RecoveryToken.objects.select_related("socio").filter(token_hash=digest, usado=False, fecha_expira__gt=timezone.now(), socio__estado="ACTIVA").first()
    return token.socio if token else None


@transaction.atomic
def complete_reset(raw, password):
    digest = hashlib.sha256(raw.encode()).hexdigest()
    reference = RecoveryToken.objects.filter(token_hash=digest).first()
    if not reference: raise ValidationError("Enlace inválido o vencido.")
    user = User.objects.select_for_update().get(pk=reference.socio_id)
    token = RecoveryToken.objects.select_for_update().get(pk=digest)
    if token.usado or token.fecha_expira <= timezone.now() or not user.is_active:
        raise ValidationError("Enlace inválido o vencido.")
    user.set_password(password)
    user.failed_attempts=0; user.locked_until=None
    user.save(update_fields=["password", "failed_attempts", "locked_until"])
    RecoveryToken.objects.filter(socio=user, usado=False).update(usado=True)
    audit(user,user,"Contraseña restablecida")


@transaction.atomic
def set_member_state(pk,status,actor):
    user=User.objects.select_for_update().get(pk=pk)
    if status not in User.Status.values: raise ValidationError("Estado inválido.")
    previous=user.estado; user.estado=status; user.save(update_fields=["estado"])
    audit(user,actor,"Cambio de estado",f"{previous} → {status}")
    return user
