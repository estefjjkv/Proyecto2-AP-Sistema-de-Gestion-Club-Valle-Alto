from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import User
from accounts.permissions import member_only, permitted
from guests.models import GuestVisit
from instalaciones.models import Instalacion
from instalaciones.services import VIGENTES
from .forms import AdminReservaForm, ReservaForm
from .models import Reserva, ReservaServicio
from .services import (cancelar_reserva, crear_reserva, disponibilidad, modificar_reserva,
                       puede_gestionar_socio)

PESTAÑAS = {"activas": ("PENDIENTE", "CONFIRMADA"), "finalizadas": ("FINALIZADA",), "canceladas": ("CANCELADA",)}
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _con_servicios(consulta):
    return consulta.select_related("instalacion", "estado").prefetch_related(
        Prefetch("servicios", queryset=ReservaServicio.objects.select_related("servicio")))


def _invitados(reserva):
    return (GuestVisit.objects.filter(Q(id_reserva=reserva.pk) | Q(socio_id=reserva.socio_id, fecha_visita=reserva.fecha,
                                                                  instalacion_id=reserva.instalacion_id))
            .select_related("invitado", "relacion"))


def _panel_disponibilidad(form, reserva=None):
    """Instalación y fecha para el panel lateral, tomadas del formulario (enviado o inicial)."""
    def valor(campo):
        if form.is_bound:
            return form.cleaned_data.get(campo) if hasattr(form, "cleaned_data") else None
        return form.initial.get(campo)
    instalacion, fecha = valor("instalacion"), valor("fecha")
    if instalacion and not isinstance(instalacion, Instalacion):
        instalacion = Instalacion.objects.filter(pk=instalacion).first()
    if isinstance(fecha, str):
        try:
            fecha = date.fromisoformat(fecha)
        except ValueError:
            fecha = None
    if not instalacion or not fecha:
        return {"instalacion": instalacion, "fecha": fecha, "franjas": []}
    return {"instalacion": instalacion, "fecha": fecha,
            "franjas": disponibilidad(instalacion, fecha, excluir=reserva.pk if reserva else None)}


def _error(form, error):
    form.add_error(None, " ".join(error.messages))


# --- Socio --------------------------------------------------------------

@member_only
def mis_reservas_view(request):
    pestaña = request.GET.get("estado") if request.GET.get("estado") in PESTAÑAS else "activas"
    propias = Reserva.objects.filter(socio_id=request.user.pk)
    reservas = _con_servicios(propias.filter(estado_id__in=PESTAÑAS[pestaña]))
    reservas = reservas.order_by("fecha", "hora_inicio") if pestaña == "activas" else reservas.order_by("-fecha", "-hora_inicio")
    conteos = {nombre: propias.filter(estado_id__in=estados).count() for nombre, estados in PESTAÑAS.items()}
    return render(request, "reservas/mis_reservas.html", {"reservas": reservas, "pestaña": pestaña,
                  "conteos": conteos, "nav_activo": "reservas"})


@member_only
@require_http_methods(["GET", "POST"])
def nueva_reserva_view(request):
    inicial = {"fecha": timezone.localdate() + timedelta(days=1), "numero_personas": 1,
               "instalacion": request.GET.get("instalacion")}
    form = ReservaForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            reserva = crear_reserva(form.cleaned_data, request.user)
        except ValidationError as error:
            _error(form, error)
        else:
            messages.success(request, "Solicitud registrada. Le avisaremos por correo cuando administración la confirme.")
            return redirect("reservas:detalle", pk=reserva.pk)
    return render(request, "reservas/nueva_reserva.html", {"form": form, "panel": _panel_disponibilidad(form),
                  "nav_activo": "reservas"})


@member_only
@require_http_methods(["GET", "POST"])
def modificar_reserva_view(request, pk):
    reserva = get_object_or_404(Reserva.objects.select_related("instalacion"), pk=pk, socio_id=request.user.pk)
    if not puede_gestionar_socio(reserva):
        messages.error(request, "Esta reserva ya no se puede modificar.")
        return redirect("reservas:detalle", pk=pk)
    form = ReservaForm(request.POST or None, reserva=reserva)
    if request.method == "POST" and form.is_valid():
        try:
            modificar_reserva(pk, form.cleaned_data, request.user)
        except ValidationError as error:
            _error(form, error)
        else:
            messages.success(request, "Reserva modificada. Queda pendiente de una nueva confirmación.")
            return redirect("reservas:detalle", pk=pk)
    return render(request, "reservas/nueva_reserva.html", {"form": form, "reserva": reserva,
                  "panel": _panel_disponibilidad(form, reserva), "nav_activo": "reservas"})


@member_only
def detalle_reserva_view(request, pk):
    reserva = get_object_or_404(_con_servicios(Reserva.objects), pk=pk, socio_id=request.user.pk)
    lineas = list(reserva.servicios.all())
    return render(request, "reservas/detalle_reserva.html", {
        "reserva": reserva, "lineas": lineas, "total_servicios": sum(l.subtotal for l in lineas),
        "invitados": _invitados(reserva), "gestionable": puede_gestionar_socio(reserva), "nav_activo": "reservas"})


@member_only
@require_POST
def cancelar_reserva_view(request, pk):
    get_object_or_404(Reserva, pk=pk, socio_id=request.user.pk)
    try:
        cancelar_reserva(pk, request.user)
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
        return redirect("reservas:detalle", pk=pk)
    messages.success(request, "Reserva cancelada. El horario quedó liberado.")
    return redirect("reservas:mis_reservas")


@login_required
@require_GET
def disponibilidad_view(request):
    socio = isinstance(request.user, User)
    if not socio and not request.user.has_perm("accounts.manage_facilities"):
        raise PermissionDenied
    instalacion = Instalacion.objects.filter(pk=request.GET.get("instalacion", "")).first()
    try:
        fecha = date.fromisoformat(request.GET.get("fecha", ""))
    except ValueError:
        fecha = None
    if instalacion is None or fecha is None:
        return JsonResponse({"error": "Indique instalación y fecha válidas."}, status=400)
    excluir = request.GET.get("excluir")
    # Un socio solo puede excluir (al modificar) una reserva propia.
    if excluir and not (excluir.isdigit() and (not socio or Reserva.objects.filter(pk=excluir, socio_id=request.user.pk).exists())):
        excluir = None
    return JsonResponse({"instalacion": instalacion.nombre, "fecha": fecha.strftime("%d/%m/%Y"),
                         "aforo": instalacion.aforo_maximo, "franjas": disponibilidad(instalacion, fecha, excluir)})


# --- Administración -------------------------------------------------------

def _lunes(dia):
    return dia - timedelta(days=dia.weekday())


def _texto_semana(lunes):
    domingo = lunes + timedelta(days=6)
    if lunes.month == domingo.month:
        return f"{lunes.day} - {domingo.day} {MESES[lunes.month - 1]} {lunes.year}"
    return f"{lunes.day} {MESES[lunes.month - 1]} - {domingo.day} {MESES[domingo.month - 1]} {domingo.year}"


@permitted("manage_facilities")
def calendario_view(request):
    hoy = timezone.localdate()
    try:
        lunes = _lunes(date.fromisoformat(request.GET.get("semana", "")))
    except ValueError:
        lunes = _lunes(hoy)
    semanas = [_lunes(hoy) + timedelta(weeks=n) for n in range(-4, 9)]
    if lunes not in semanas:
        semanas = sorted(semanas + [lunes])
    codigo = request.GET.get("instalacion", "")
    dias = [lunes + timedelta(days=n) for n in range(7)]

    reservas = (Reserva.objects.filter(fecha__range=(dias[0], dias[-1]), estado_id__in=VIGENTES + ("FINALIZADA",))
                .select_related("instalacion", "socio").order_by("hora_inicio", "instalacion__nombre"))
    if codigo:
        reservas = reservas.filter(instalacion_id=codigo)
    filas = {}
    for r in reservas:
        filas.setdefault(r.hora_inicio, [[] for _ in dias])[(r.fecha - lunes).days].append(r)

    pendientes = (Reserva.objects.filter(estado_id="PENDIENTE", fecha__gte=hoy)
                  .select_related("instalacion", "socio").order_by("fecha", "hora_inicio"))
    return render(request, "reservas/admin_calendario.html", {
        "instalaciones": Instalacion.objects.order_by("nombre"), "codigo": codigo,
        "semanas": [(s.isoformat(), _texto_semana(s)) for s in semanas], "semana": lunes.isoformat(),
        "dias": [(d, f"{DIAS[i]} {d.day}") for i, d in enumerate(dias)], "hoy": hoy,
        "filas": sorted(filas.items()), "pendientes": pendientes, "menu_admin": "reservas"})


@permitted("manage_facilities")
@require_http_methods(["GET", "POST"])
def admin_nueva_view(request):
    inicial = {"fecha": request.GET.get("fecha") or timezone.localdate() + timedelta(days=1),
               "numero_personas": 1, "instalacion": request.GET.get("instalacion")}
    form = AdminReservaForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            reserva = crear_reserva(form.cleaned_data, request.user)
        except ValidationError as error:
            _error(form, error)
        else:
            messages.success(request, "Reserva creada y confirmada. Se notificó al socio.")
            return redirect("reservas:administrar", pk=reserva.pk)
    return render(request, "reservas/admin_detalle.html", {"form": form, "panel": _panel_disponibilidad(form),
                  "menu_admin": "reservas"})


@permitted("manage_facilities")
@require_http_methods(["GET", "POST"])
def administrar_view(request, pk):
    reserva = get_object_or_404(_con_servicios(Reserva.objects).select_related("socio"), pk=pk)
    vigente = reserva.estado_id in VIGENTES
    form = AdminReservaForm(request.POST or None, reserva=reserva)
    if not vigente:
        for campo in form.fields.values():
            campo.disabled = True
    if request.method == "POST" and vigente and form.is_valid():
        confirmar = request.POST.get("accion") == "confirmar"
        try:
            modificar_reserva(pk, form.cleaned_data, request.user, confirmar=confirmar)
        except ValidationError as error:
            _error(form, error)
        else:
            messages.success(request, "Reserva confirmada. Se notificó al socio." if confirmar else "Cambios guardados.")
            return redirect("reservas:administrar", pk=pk)
    return render(request, "reservas/admin_detalle.html", {
        "form": form, "reserva": reserva, "vigente": vigente, "invitados": _invitados(reserva),
        "historial": reserva.historial.all(), "panel": _panel_disponibilidad(form, reserva), "menu_admin": "reservas"})


@permitted("manage_facilities")
@require_POST
def admin_cancelar_view(request, pk):
    get_object_or_404(Reserva, pk=pk)
    try:
        cancelar_reserva(pk, request.user, request.POST.get("motivo", "").strip()[:200])
    except ValidationError as error:
        messages.error(request, " ".join(error.messages))
    else:
        messages.success(request, "Reserva cancelada. Se notificó al socio.")
    return redirect("reservas:administrar", pk=pk)
