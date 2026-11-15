from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST, require_http_methods
from .forms import RegistroSocioForm, PerfilForm, LoginForm, AdminCreateForm, AdminEditForm, RecoveryRequestForm
from .models import User, Administrator, AccountEvent
from .permissions import member_only, permitted
from .services import send_password_reset, set_member_state, audit, get_reset_user, complete_reset


class ClubLoginView(LoginView):
    template_name = "usuarios/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if isinstance(user, Administrator):
            if user.rol_id == "RECEPCION": return reverse_lazy("invitados:recepcion")
            return reverse_lazy("administradores:panel")
        return reverse_lazy("socios:inicio")


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("usuarios:login")
    form = RegistroSocioForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                user = form.save()
                audit(user, user, "Registro de socio")
        except IntegrityError:
            form.add_error(None, "El correo o la cédula ya están registrados.")
        else:
            messages.success(request, "Cuenta creada. Ya puede iniciar sesión con su correo.")
            return redirect("usuarios:login")
    return render(request, "socios/registro.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("usuarios:login")


@require_http_methods(["GET", "POST"])
def recover(request):
    form = RecoveryRequestForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        if send_password_reset(form.cleaned_data["email"]):
            return redirect("usuarios:recuperar_enviado")
        form.add_error(None, "No pudimos procesar la solicitud de correo. Inténtelo más tarde.")
    return render(request, "usuarios/recuperar.html", {"form": form})


@sensitive_post_parameters("new_password1", "new_password2")
@never_cache
@require_http_methods(["GET", "POST"])
def reset_confirm(request, token):
    # Cambiar URL a un marcador después de recibir el token evita propagarlo a otros recursos.
    if token != "establecer":
        if get_reset_user(token):
            request.session["reset_token"] = token
            return redirect("usuarios:reset_confirm", token="establecer")
        return render(request,"usuarios/reset_confirm.html",{"validlink":False})
    raw = request.session.get("reset_token", "")
    user = get_reset_user(raw)
    if not user: return render(request,"usuarios/reset_confirm.html",{"validlink":False})
    form = SetPasswordForm(user, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try: complete_reset(raw, form.cleaned_data["new_password1"])
        except ValidationError as error: form.add_error(None,error)
        else:
            request.session.pop("reset_token",None)
            return redirect("usuarios:reset_complete")
    return render(request,"usuarios/reset_confirm.html",{"validlink":True,"form":form})


@member_only
def home(request):
    membership = getattr(request.user, "membresia", None)
    return render(request, "socios/inicio.html", {"membresia": membership, "nav_activo": "inicio"})


@member_only
@require_http_methods(["GET", "POST"])
def profile(request):
    form = PerfilForm(request.POST if request.method == "POST" else None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(None, "Correo o cédula ya registrados.")
        else:
            messages.success(request, "Perfil actualizado.")
            return redirect("socios:perfil")
    return render(request, "socios/perfil.html", {"form": form, "nav_activo": "perfil"})


@permitted("manage_members")
def member_list(request):
    members = User.objects.all().order_by("nombre_completo", "pk")
    search = request.GET.get("q", "").strip()
    if search:
        members = members.filter(Q(nombre_completo__icontains=search) | Q(cedula__icontains=search) | Q(email__icontains=search))
    return render(request, "socios/admin_lista.html", {"socios": members, "q": search, "menu_admin": "socios"})


@permitted("manage_members")
@require_http_methods(["GET", "POST"])
def member_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        action = request.POST.get("accion")
        if action == "estado":
            try:
                set_member_state(pk, request.POST.get("estado"), request.user)
                messages.success(request, "Estado actualizado.")
            except ValidationError as error:
                messages.error(request, " ".join(error.messages))
        elif action == "reset":
            if send_password_reset(user.email):
                audit(user,request.user,"Solicitud de recuperación")
                messages.success(request, "Si la cuenta está activa, recibirá un enlace para elegir una nueva contraseña.")
            else:
                messages.error(request, "No fue posible enviar el correo. Revise la configuración.")
        else:
            messages.error(request, "Acción inválida.")
        return redirect("socios:gestion_detalle", pk=pk)
    return render(request, "socios/admin_detalle.html", {"socio": user, "eventos": AccountEvent.objects.filter(target_kind="socio",target_id=user.pk), "estados": User.Status.choices, "menu_admin": "socios"})


@login_required
def dashboard(request):
    if isinstance(request.user, User):
        return redirect("socios:inicio")
    if request.user.rol_id == "RECEPCION":
        return redirect("invitados:recepcion")
    from memberships.models import Membership
    from guests.models import GuestVisit
    from django.utils import timezone
    return render(request, "administradores/panel.html", {
        "socios_activos": User.objects.filter(estado="ACTIVA").count(),
        "membresias_activas": Membership.objects.filter(estado="ACTIVA", fecha_inscripcion__lte=timezone.localdate(), fecha_renovacion__gte=timezone.localdate()).count(),
        "invitados_hoy": GuestVisit.objects.filter(fecha_visita=timezone.localdate()).count(), "menu_admin": "inicio"})


@permitted("manage_administrators")
@require_http_methods(["GET", "POST"])
def admin_users(request, pk=None):
    target = get_object_or_404(Administrator, pk=pk) if pk else None
    form_cls = AdminEditForm if target else AdminCreateForm
    form = form_cls(request.POST if request.method == "POST" else None, instance=target)
    if request.method == "POST" and form.is_valid():
        if target and target.pk == request.user.pk and (form.cleaned_data["rol"].pk != request.user.rol_id or not form.cleaned_data["activo"]):
            form.add_error(None, "No puede quitarse sus propios permisos ni desactivar su cuenta.")
        else:
            try:
                with transaction.atomic():
                    saved = form.save()
                    audit(saved,request.user,"Administrador actualizado" if target else "Administrador creado",f"Rol: {saved.rol_id}; activa: {saved.activo}")
            except IntegrityError:
                form.add_error(None, "Correo o cédula ya registrados.")
            else:
                messages.success(request, "Cuenta administrativa guardada.")
                return redirect("administradores:gestion")
    return render(request, "administradores/gestion.html", {"form": form, "editando": target,
        "administradores": Administrator.objects.select_related("rol").order_by("nombre_completo"), "menu_admin": "administradores"})


@permitted("manage_administrators")
@sensitive_post_parameters("new_password1", "new_password2")
@never_cache
@require_http_methods(["GET", "POST"])
def admin_password(request, pk):
    target = get_object_or_404(Administrator, pk=pk)
    form = SetPasswordForm(target, request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            target = Administrator.objects.select_for_update().get(pk=pk)
            target.set_password(form.cleaned_data["new_password1"])
            target.failed_attempts = 0
            target.locked_until = None
            target.save(update_fields=["password", "failed_attempts", "locked_until"])
            audit(target, request.user, "Contraseña administrativa restablecida")
        if request.user.pk == target.pk:
            update_session_auth_hash(request, target)
        messages.success(request, "Contraseña actualizada; se limpiaron los intentos fallidos.")
        return redirect("administradores:gestion")
    return render(request, "administradores/clave.html", {"form": form, "cuenta": target})
