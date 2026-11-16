from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseNotAllowed
from django.shortcuts import render


# Módulos que todavía son prototipos estáticos. Al implementar uno, se quita de
# aquí y sus vistas se protegen con accounts.permissions (permitted/member_only).
MODULOS_PENDIENTES = {"notificaciones"}


class AccessMiddleware:
    """Protege también los prototipos del otro equipo; no implementa sus módulos."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        namespace = match.namespace
        if namespace not in MODULOS_PENDIENTES:
            return None
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        admin_names = {"gestion", "bloqueos", "ocupacion", "reportes", "calendario", "administrar", "pagos", "centro"}
        if match.url_name in admin_names:
            permission = "manage_billing" if namespace == "estado_cuenta" else "manage_facilities"
            if namespace == "notificaciones":
                permission = "view_notifications"
            if not request.user.has_perm("accounts." + permission):
                raise PermissionDenied
        if request.method not in {"GET", "HEAD"}:
            return HttpResponseNotAllowed(["GET", "HEAD"])
        return render(request, "integration_pending.html", {"modulo": namespace.replace("_", " ")})
