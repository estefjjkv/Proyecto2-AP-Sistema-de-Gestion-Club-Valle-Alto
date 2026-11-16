from datetime import date
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from accounts.models import User
from memberships.models import Membership, MembershipType
from memberships.services import require_active_member
from instalaciones.models import Instalacion
from .models import Guest, GuestVisit, GuestEntry


@transaction.atomic
def register_guest(user,data):
    user=User.objects.select_for_update().get(pk=user.pk)
    require_active_member(user)
    ref=Membership.objects.filter(socio=user).first()
    if not ref: raise ValidationError("Debe asociar una membresía antes de registrar invitados.")
    kind=MembershipType.objects.select_for_update().get(pk=ref.tipo_id)
    member=Membership.objects.select_for_update().get(pk=ref.pk)
    day=data["fecha_visita"]
    if not member.vigente: raise ValidationError("Su membresía debe estar activa y vigente.")
    if day<timezone.localdate() or not member.fecha_inscripcion<=day<=member.fecha_renovacion: raise ValidationError("La visita debe estar dentro de la vigencia y no ser pasada.")
    used=GuestVisit.objects.filter(socio=user,fecha_visita__year=day.year,fecha_visita__month=day.month).count()
    if used>=kind.limite_invitados: raise ValidationError("Alcanzó el límite de invitados para el mes de la visita.")
    facility=Instalacion.objects.get(pk=data["instalacion"].pk)
    if not facility.activa: raise ValidationError("La instalación no está disponible.")
    if data["cedula"]==user.cedula: raise ValidationError("No puede registrarse como su propio invitado.")
    guest,created=Guest.objects.get_or_create(cedula=data["cedula"],defaults={"nombre_completo":data["nombre_completo"]})
    if not created and guest.nombre_completo.strip().casefold()!=data["nombre_completo"].strip().casefold():
        raise ValidationError("La cédula del invitado ya está registrada con otro nombre. Solicite revisión a administración.")
    visit=GuestVisit(socio=user,invitado=guest,fecha_visita=day,instalacion=facility,relacion=data["relacion"])
    visit.full_clean();visit.save(force_insert=True);return visit


def visit_key(reference):
    try:
        socio,guest,day,facility=signing.loads(reference,salt="guest-entry")
        return (socio,guest,date.fromisoformat(day),facility)
    except (signing.BadSignature,ValueError,TypeError):raise ValidationError("Referencia de visita inválida.")


@transaction.atomic
def check_in(reference):
    key=visit_key(reference)
    # Orden de bloqueos consistente con registro y suspensión.
    user=User.objects.select_for_update().get(pk=key[0]);require_active_member(user)
    member=Membership.objects.select_for_update().get(pk=user.pk)
    visit=GuestVisit.objects.select_for_update(of=("self",)).select_related("instalacion").get(pk=key)
    if visit.fecha_visita!=timezone.localdate():raise ValidationError("Solo puede registrar ingresos previstos para hoy.")
    if not member.vigente or not visit.instalacion.activa:raise ValidationError("La membresía o instalación no están habilitadas.")
    entry,created=GuestEntry.objects.get_or_create(socio=key[0],invitado=key[1],fecha_visita=key[2],instalacion=key[3])
    if not created:raise ValidationError("El ingreso ya fue registrado.")
    return entry
