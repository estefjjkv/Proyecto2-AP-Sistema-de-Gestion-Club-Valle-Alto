from collections import defaultdict

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.permissions import member_only, permitted
from .forms import BloqueoForm, InstalacionForm, OcupacionForm, ReporteForm, ServicioForm
from .models import BloqueoInstalacion, Instalacion, ServicioAdicional
from .services import bloqueo_actual, crear_bloqueo, guardar_instalacion, ocupacion, reporte_uso

# Iniciales que se muestran en lugar de imagen, según el tipo de instalación.
ICONOS = {"GOLF": "GO", "TENIS": "TE", "PISCINA": "PI", "SALON_EVENTOS": "EV"}


def _error(form, error):
    if isinstance(error, ValidationError):
        form.add_error(None, " ".join(error.messages))
    else:
        form.add_error(None, "El registro entra en conflicto con otro existente o fue modificado. Revise los datos.")


def _tarjetas(instalaciones):
    servicios = defaultdict(list)
    for servicio in ServicioAdicional.objects.filter(activo=True).order_by("nombre"):
        servicios[servicio.tipo_instalacion_id].append(servicio)
    return [{"instalacion": i, "icono": ICONOS.get(i.tipo_id, i.nombre[:2].upper()),
             "servicios": servicios[i.tipo_id], "bloqueo": bloqueo_actual(i)} for i in instalaciones]


@member_only
def catalogo_view(request):
    instalaciones = Instalacion.objects.filter(activa=True).select_related("tipo").order_by("nombre")
    return render(request, "instalaciones/catalogo.html", {"tarjetas": _tarjetas(instalaciones), "nav_activo": "instalaciones"})


@permitted("manage_facilities")
def admin_lista_view(request):
    instalaciones = Instalacion.objects.select_related("tipo").order_by("-activa", "nombre")
    return render(request, "instalaciones/admin_lista.html", {"tarjetas": _tarjetas(instalaciones), "menu_admin": "instalaciones"})


@permitted("manage_facilities")
@require_http_methods(["GET", "POST"])
def admin_form_view(request, codigo=None):
    instalacion = get_object_or_404(Instalacion, pk=codigo) if codigo else None
    form = InstalacionForm(request.POST or None, instance=instalacion)
    if request.method == "POST" and form.is_valid():
        try:
            guardada = guardar_instalacion(form.cleaned_data, codigo)
        except (ValidationError, IntegrityError) as error:
            _error(form, error)
        else:
            messages.success(request, f"Instalación {guardada.nombre} guardada.")
            return redirect("instalaciones:gestion")
    return render(request, "instalaciones/admin_form.html", {"form": form, "instalacion": instalacion, "menu_admin": "instalaciones"})


@permitted("manage_facilities")
@require_http_methods(["GET", "POST"])
def admin_servicios_view(request, codigo=None):
    servicio = get_object_or_404(ServicioAdicional, pk=codigo) if codigo else None
    form = ServicioForm(request.POST or None, instance=servicio)
    if request.method == "POST" and form.is_valid():
        try:
            form.save()
        except IntegrityError as error:
            _error(form, error)
        else:
            messages.success(request, "Servicio adicional guardado.")
            return redirect("instalaciones:servicios")
    servicios = ServicioAdicional.objects.select_related("tipo_instalacion").order_by("tipo_instalacion__descripcion", "nombre")
    return render(request, "instalaciones/admin_servicios.html", {"form": form, "servicio": servicio,
                  "servicios": servicios, "menu_admin": "instalaciones"})


@permitted("manage_facilities")
@require_http_methods(["GET", "POST"])
def admin_bloqueos_view(request):
    inicial = {"instalacion": request.GET.get("instalacion")}
    form = BloqueoForm(request.POST or None, initial=inicial)
    if request.method == "POST" and form.is_valid():
        try:
            crear_bloqueo(form.cleaned_data, request.user)
        except (ValidationError, IntegrityError) as error:
            _error(form, error)
        else:
            messages.success(request, "Bloqueo registrado.")
            return redirect("instalaciones:bloqueos")
    bloqueos = (BloqueoInstalacion.objects.filter(fin__gt=timezone.now())
                .select_related("instalacion", "motivo").order_by("inicio"))
    return render(request, "instalaciones/admin_bloqueos.html", {"form": form, "bloqueos": bloqueos, "menu_admin": "instalaciones"})


@permitted("manage_facilities")
@require_POST
def admin_bloqueo_eliminar_view(request, pk):
    get_object_or_404(BloqueoInstalacion, pk=pk).delete()
    messages.success(request, "Bloqueo eliminado.")
    return redirect("instalaciones:bloqueos")


@permitted("manage_facilities")
def admin_ocupacion_view(request):
    ahora = timezone.localtime()
    datos = request.GET if "fecha" in request.GET else {"fecha": ahora.date(), "hora": min(max(ahora.hour, 5), 22)}
    form = OcupacionForm(datos)
    filas, desde, hasta = [], None, None
    if form.is_valid():
        desde, hasta = form.franja()
        filas = ocupacion(form.cleaned_data["fecha"], desde, hasta)
    return render(request, "instalaciones/admin_ocupacion.html", {"form": form, "filas": filas,
                  "desde": desde, "hasta": hasta, "menu_admin": "instalaciones"})


@permitted("manage_facilities")
def admin_reportes_view(request):
    form = ReporteForm(request.GET if "periodo" in request.GET else None)
    if form.is_bound and form.is_valid():
        periodo = form.cleaned_data["periodo"]
    else:
        periodo = timezone.localdate().replace(day=1)
        form = ReporteForm(initial={"periodo": periodo.isoformat()})
    return render(request, "instalaciones/admin_reportes.html", {"form": form, "periodo": periodo,
                  "reporte": reporte_uso(periodo), "menu_admin": "instalaciones"})
