from datetime import datetime, time

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from accounts.permissions import permitted
from core.models import CatTipoNotificacion
from estado_cuenta.services import siguiente_mes
from .forms import MARCADORES, FiltroForm, PlantillaForm
from .models import Notificacion, PlantillaNotificacion
from .services import enviar

ICONOS = {"NUEVO_SOCIO": "RS", "RESERVA_CONFIRMADA": "RE", "RESERVA_MODIFICADA": "RM", "RESERVA_CANCELADA": "CA",
          "NUEVO_ESTADO_CUENTA": "EC", "PAGO_POR_VENCER": "PV", "PAGO_VENCIDO": "VE"}


@permitted("view_notifications")
def centro_view(request):
    form = FiltroForm(request.GET or None)
    notificaciones = Notificacion.objects.select_related("socio", "tipo", "estado")
    if form.is_bound and form.is_valid():
        datos = form.cleaned_data
        if datos["q"].strip():
            q = datos["q"].strip()
            notificaciones = notificaciones.filter(Q(correo_destino__icontains=q) | Q(socio__nombre_completo__icontains=q)
                                                   | Q(socio__cedula__icontains=q))
        if datos["tipo"]:
            notificaciones = notificaciones.filter(tipo=datos["tipo"])
        if datos["periodo"]:
            inicio = timezone.make_aware(datetime.combine(datos["periodo"], time.min))
            fin = timezone.make_aware(datetime.combine(siguiente_mes(datos["periodo"]), time.min))
            notificaciones = notificaciones.filter(fecha_creacion__gte=inicio, fecha_creacion__lt=fin)
        if datos["estado"]:
            notificaciones = notificaciones.filter(estado_id=datos["estado"])
    pagina = Paginator(notificaciones.order_by("-fecha_creacion", "-pk"), 25).get_page(request.GET.get("pagina"))
    filtros = request.GET.copy()
    filtros.pop("pagina", None)

    plantillas = {p.tipo_id: p for p in PlantillaNotificacion.objects.all()}
    tarjetas = [{"tipo": t, "icono": ICONOS.get(t.codigo, t.codigo[:2]), "plantilla": plantillas.get(t.codigo)}
                for t in CatTipoNotificacion.objects.order_by("descripcion")]
    return render(request, "notificaciones/centro.html", {
        "form": form, "pagina": pagina, "filtros": filtros.urlencode(), "tarjetas": tarjetas,
        "menu_admin": "notificaciones"})


@permitted("view_notifications")
@require_POST
def reenviar_view(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)
    if notificacion.estado_id == "ENVIADA":
        messages.info(request, "Esa notificación ya fue enviada.")
    elif enviar(notificacion.pk):
        messages.success(request, f"Notificación reenviada a {notificacion.correo_destino}.")
    else:
        messages.error(request, "No se pudo enviar el correo. Revise la configuración de correo e intente más tarde.")
    volver = request.POST.get("volver", "")
    if url_has_allowed_host_and_scheme(volver, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(volver)
    return redirect("notificaciones:centro")


@permitted("manage_templates")
@require_http_methods(["GET", "POST"])
def plantilla_view(request, tipo):
    plantilla = get_object_or_404(PlantillaNotificacion.objects.select_related("tipo", "admin"), pk=tipo)
    form = PlantillaForm(request.POST or None, instance=plantilla)
    if request.method == "POST" and form.is_valid():
        plantilla = form.save(commit=False)
        plantilla.admin_id = request.user.pk
        plantilla.fecha_actualizacion = timezone.now()
        plantilla.save()
        messages.success(request, f"Plantilla «{plantilla.tipo}» guardada. Se usará en los próximos envíos.")
        return redirect("notificaciones:centro")
    ejemplo = plantilla.renderizar(nombre="María López", detalle="(detalle del evento)") if not form.errors else None
    return render(request, "notificaciones/plantilla.html", {"form": form, "plantilla": plantilla, "ejemplo": ejemplo,
                  "marcadores": MARCADORES, "menu_admin": "notificaciones"})
