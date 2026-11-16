from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

PERMISSION_MAP = {
    "manage_members": "GESTIONAR_SOCIOS", "manage_administrators": "GESTIONAR_ADMINS",
    "manage_memberships": "GESTIONAR_MEMBRESIAS", "view_reception": "CONSULTAR_INVITADOS",
    "manage_facilities": "GESTIONAR_INSTALACIONES", "manage_billing": "GESTIONAR_COBROS",
    "manage_templates": "GESTIONAR_PLANTILLAS", "view_notifications": "CONSULTAR_NOTIFICACIONES",
}

def permitted(code):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.has_perm("accounts." + code): raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

def member_only(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .models import User
        if not isinstance(request.user, User): raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped
