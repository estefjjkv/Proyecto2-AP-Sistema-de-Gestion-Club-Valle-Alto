from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from accounts.models import User
from accounts.permissions import member_only, permitted
from .forms import SelectTypeForm, MembershipForm, TypeForm, BeneficiaryForm
from .models import Membership, MembershipType, Beneficiary
from .services import enroll, save_membership, save_type, save_beneficiary


def form_error(form, error):
    form.add_error(None, " ".join(error.messages) if isinstance(error, ValidationError) else "El registro ya existe o fue modificado. Revise los datos.")


@member_only
@require_http_methods(["GET", "POST"])
def mine(request):
    membership = Membership.objects.select_related("tipo").filter(socio=request.user).first()
    form = SelectTypeForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            enroll(request.user, form.cleaned_data["tipo"].pk)
        except (ValidationError, IntegrityError) as error:
            form_error(form, error)
        else:
            messages.success(request, "Membresía asociada a su cuenta.")
            return redirect("membresias:mi_membresia")
    return render(request, "membresias/mi_membresia.html", {"membresia": membership, "form": form,
        "tipos": MembershipType.objects.all(), "nav_activo": "membresia"})


@permitted("manage_memberships")
def listing(request):
    return render(request, "membresias/admin_lista.html", {
        "membresias": Membership.objects.select_related("socio", "tipo").order_by("socio__nombre_completo"), "menu_admin": "membresias"})


@permitted("manage_memberships")
@require_http_methods(["GET", "POST"])
def edit(request, pk=None):
    obj = get_object_or_404(Membership, pk=pk) if pk else None
    form = MembershipForm(request.POST if request.method == "POST" else None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            member = save_membership(form.cleaned_data, request.user, pk)
        except (ValidationError, IntegrityError) as error:
            form_error(form, error)
        else:
            messages.success(request, "Membresía guardada e historial actualizado.")
            return redirect("membresias:editar", pk=member.pk)
    return render(request, "membresias/admin_form.html", {"form": form, "membresia": obj, "menu_admin": "membresias"})


@permitted("manage_memberships")
@require_http_methods(["GET", "POST"])
def types(request, pk=None):
    obj = get_object_or_404(MembershipType, pk=pk) if pk else None
    form = TypeForm(request.POST if request.method == "POST" else None, instance=obj)
    if request.method == "POST" and form.is_valid():
        try:
            save_type(form.cleaned_data, pk)
        except (ValidationError, IntegrityError) as error:
            form_error(form, error)
        else:
            messages.success(request, "Tipo guardado. Las cuotas de membresías existentes se conservan; los límites se actualizan.")
            return redirect("membresias:tipos")
    return render(request, "membresias/tipos.html", {"form": form, "tipos": MembershipType.objects.all(), "editando": obj, "menu_admin": "membresias"})


def accessible_membership(request, membership_id):
    obj = get_object_or_404(Membership, pk=membership_id)
    if not (isinstance(request.user, User) and obj.socio_id == request.user.pk) and not request.user.has_perm("accounts.manage_memberships"):
        raise PermissionDenied
    return obj


@login_required
@require_http_methods(["GET", "POST"])
def beneficiary(request, membership_id, pk=None):
    membership = accessible_membership(request, membership_id)
    obj = get_object_or_404(Beneficiary, cedula=pk, membresia=membership) if pk else None
    form = BeneficiaryForm(request.POST if request.method == "POST" else None, instance=obj)
    is_admin = request.user.has_perm("accounts.manage_memberships")
    if request.method == "POST" and form.is_valid():
        try:
            save_beneficiary(membership.pk, form.cleaned_data, pk)
        except (ValidationError, IntegrityError) as error:
            form_error(form, error)
        else:
            messages.success(request, "Beneficiario guardado.")
            return redirect("membresias:editar", pk=membership.pk) if is_admin else redirect("membresias:mi_membresia")
    return render(request, "membresias/beneficiario_form.html", {"form": form, "membresia": membership,
        "base_template": "base_admin.html" if is_admin else "base.html", "menu_admin": "membresias", "nav_activo": "membresia"})


@login_required
@require_POST
def delete_beneficiary(request, membership_id, pk):
    membership = accessible_membership(request, membership_id)
    get_object_or_404(Beneficiary, cedula=pk, membresia=membership).delete()
    messages.success(request, "Beneficiario eliminado.")
    if request.user.has_perm("accounts.manage_memberships"):
        return redirect("membresias:editar", pk=membership.pk)
    return redirect("membresias:mi_membresia")
