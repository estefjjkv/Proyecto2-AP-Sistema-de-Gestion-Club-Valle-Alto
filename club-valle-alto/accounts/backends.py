from datetime import timedelta
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.db import transaction
from django.utils import timezone
from .models import User, Administrator, RolePermission
from .permissions import PERMISSION_MAP


class IdentityBackend(BaseBackend):
    model = User
    kind = "socio"
    def authenticate(self, request, username=None, password=None, cuenta="socio", **kwargs):
        if cuenta != self.kind or not username or password is None: return None
        # Bloquear SOLO la identidad evita mezclar socios/administradores con igual cédula.
        with transaction.atomic():
            user = self.model.objects.select_for_update().filter(email__iexact=username.strip()).first()
            if user is None:
                self.model().set_password(password)
                return None
            now = timezone.now()
            if user.locked_until and user.locked_until > now: return None
            if user.locked_until:
                user.failed_attempts = 0
                user.locked_until = None
            if user.check_password(password) and user.is_active:
                user.failed_attempts = 0
                user.locked_until = None
                user.save(update_fields=["failed_attempts", "locked_until"])
                return user
            user.failed_attempts = min(user.failed_attempts + 1, settings.LOGIN_FAILURE_LIMIT)
            if user.failed_attempts >= settings.LOGIN_FAILURE_LIMIT:
                user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCK_MINUTES)
            user.save(update_fields=["failed_attempts", "locked_until"])
        return None

    def get_user(self, user_id):
        user = self.model.objects.filter(pk=user_id).first()
        return user if user and user.is_active else None

    def has_perm(self, user_obj, perm, obj=None):
        if obj is not None or not isinstance(user_obj, Administrator) or not user_obj.is_active: return False
        if not perm.startswith("accounts."): return False
        code = PERMISSION_MAP.get(perm.split(".", 1)[1])
        return bool(code and RolePermission.objects.filter(codigo_rol=user_obj.rol_id, codigo_permiso=code).exists())


class SocioBackend(IdentityBackend):
    pass


class AdminBackend(IdentityBackend):
    model = Administrator
    kind = "administrador"
