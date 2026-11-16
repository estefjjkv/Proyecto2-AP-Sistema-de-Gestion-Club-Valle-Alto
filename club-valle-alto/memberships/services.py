from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.utils import timezone
from accounts.models import User, Administrator
from .models import Membership, MembershipType, Beneficiary


def history_context(actor, reason):
    # GUC LOCAL: no se filtra identidad entre conexiones reutilizadas del pool.
    with connection.cursor() as cursor:
        cursor.execute("SELECT set_config('club.actor_admin', %s, true), set_config('club.motivo', %s, true)",
                       [actor.pk if isinstance(actor,Administrator) else "", reason])


def require_active_member(user):
    if not isinstance(user, User) or not user.is_active: raise ValidationError("Se necesita una cuenta de socio activa.")


@transaction.atomic
def enroll(user,type_id):
    user=User.objects.select_for_update().get(pk=user.pk)
    require_active_member(user)
    kind=MembershipType.objects.select_for_update().get(pk=type_id)
    if Membership.objects.filter(socio=user).exists(): raise ValidationError("Ya tiene una membresía. Solicite cambios a administración.")
    today=timezone.localdate()
    member=Membership(socio=user,tipo=kind,fecha_inscripcion=today,fecha_renovacion=today+timedelta(days=settings.MEMBERSHIP_DURATION_DAYS),cuota=kind.cuota)
    member.full_clean()
    history_context(None,"Inscripción del socio")
    member.save(force_insert=True) # El trigger SQL crea el historial una sola vez.
    return member


@transaction.atomic
def save_membership(data,actor,pk=None):
    user=User.objects.select_for_update().get(pk=data["socio"].pk)
    kind=MembershipType.objects.select_for_update().get(pk=data["tipo"].pk)
    member=Membership.objects.select_for_update().get(pk=pk) if pk else Membership(socio=user)
    if pk and member.socio_id != user.pk: raise ValidationError("No se puede transferir una membresía.")
    count=member.beneficiarios.count() if pk else 0
    if count>kind.limite_beneficiarios or (count and kind.codigo!="FAMILIAR"):
        raise ValidationError("El tipo no admite los beneficiarios actuales.")
    for field in ("tipo","fecha_inscripcion","fecha_renovacion","cuota","estado"): setattr(member,field,data[field])
    if member.estado=="ACTIVA":
        require_active_member(user)
        if member.fecha_renovacion<timezone.localdate(): raise ValidationError("La renovación de una membresía activa debe estar vigente.")
    member.full_clean()
    history_context(actor,data["motivo"])
    member.save(force_insert=not bool(pk))
    return member


@transaction.atomic
def save_type(data,pk=None):
    kind=MembershipType.objects.select_for_update().get(pk=pk) if pk else MembershipType()
    if pk:
        for member in kind.membership_set.all():
            count=member.beneficiarios.count()
            if count>data["limite_beneficiarios"]: raise ValidationError("El límite es menor que los beneficiarios registrados.")
    for field in ("codigo","nombre","cuota","limite_beneficiarios","limite_invitados"): setattr(kind,field,data[field])
    kind.full_clean();kind.save(force_insert=not bool(pk));return kind


@transaction.atomic
def save_beneficiary(membership_id,data,pk=None):
    user=User.objects.select_for_update().get(pk=membership_id)
    ref=Membership.objects.get(pk=membership_id)
    kind=MembershipType.objects.select_for_update().get(pk=ref.tipo_id)
    member=Membership.objects.select_for_update().get(pk=membership_id)
    require_active_member(user)
    if not member.vigente or kind.codigo!="FAMILIAR": raise ValidationError("Se necesita una membresía familiar vigente.")
    if not pk and member.beneficiarios.count()>=kind.limite_beneficiarios: raise ValidationError("Alcanzó el límite de beneficiarios.")
    beneficiary=Beneficiary.objects.get(cedula=pk,membresia=member) if pk else Beneficiary(membresia=member)
    if data["cedula"]==user.cedula: raise ValidationError("El titular no puede registrarse como beneficiario.")
    for field in ("nombre_completo","cedula","parentesco","fecha_nacimiento"):setattr(beneficiary,field,data[field])
    beneficiary.full_clean();beneficiary.save(force_insert=not bool(pk));return beneficiary


@transaction.atomic
def expire_memberships():
    history_context(None,"Vencimiento por fecha de renovación")
    return Membership.objects.filter(estado="ACTIVA",fecha_renovacion__lt=timezone.localdate()).update(estado="VENCIDA")
