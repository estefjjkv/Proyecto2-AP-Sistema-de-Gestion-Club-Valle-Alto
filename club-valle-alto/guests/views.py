from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from accounts.permissions import member_only, permitted
from memberships.models import Membership
from memberships.views import form_error
from .forms import GuestForm, ReceptionFilter
from .models import GuestVisit
from .services import register_guest, check_in


@member_only
@require_http_methods(["GET", "POST"])
def mine(request):
    form = GuestForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            register_guest(request.user, form.cleaned_data)
        except (ValidationError, IntegrityError) as error:
            form_error(form, error)
        else:
            messages.success(request, "Invitado registrado.")
            return redirect("invitados:mis_invitados")
    today = timezone.localdate()
    visits = GuestVisit.objects.filter(socio=request.user).select_related("instalacion", "invitado", "relacion")
    membership = Membership.objects.select_related("tipo").filter(socio=request.user).first()
    return render(request, "invitados/mis_invitados.html", {"form": form, "visitas": visits, "membresia": membership,
        "usados": visits.filter(fecha_visita__year=today.year, fecha_visita__month=today.month).count(),
        "nav_activo": "invitados", "hoy": today})


@permitted("view_reception")
def reception(request):
    form = ReceptionFilter(request.GET if request.GET else {"fecha": timezone.localdate()})
    visits = GuestVisit.objects.none()
    if form.is_valid():
        visits = GuestVisit.objects.filter(fecha_visita=form.cleaned_data["fecha"]).select_related("socio__membresia", "invitado", "instalacion").order_by("invitado__nombre_completo")
    return render(request, "invitados/recepcion.html", {"form": form, "visitas": visits, "es_recepcion": True, "hoy": timezone.localdate()})


@permitted("view_reception")
@require_POST
def arrival(request, pk):
    try:
        check_in(pk)
    except (ValidationError, GuestVisit.DoesNotExist, Membership.DoesNotExist) as error:
        messages.error(request, " ".join(error.messages) if isinstance(error, ValidationError) else "Visita no encontrada.")
    else:
        messages.success(request, "Ingreso registrado.")
    return redirect("invitados:recepcion")
