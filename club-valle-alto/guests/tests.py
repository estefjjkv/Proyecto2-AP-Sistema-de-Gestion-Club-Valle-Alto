from datetime import time,timedelta
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from accounts.tests import member,administrator
from memberships.services import enroll
from memberships.models import MembershipType,Membership
from instalaciones.models import Instalacion
from .models import Guest,GuestVisit,Relation,GuestEntry
from .services import register_guest,check_in

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class GuestTests(TestCase):
    def setUp(self):
        self.user=member();self.admin=administrator();self.membership=enroll(self.user,"INDIVIDUAL")
        self.facility=Instalacion.objects.create(codigo="PISCINA-1",nombre="Piscina",tipo_id="PISCINA",aforo_maximo=20,hora_apertura=time(6),hora_cierre=time(20))
        self.relation=Relation.objects.get(pk="AMIGO")
    def data(self,cedula="808880888",**changes):
        data=dict(cedula=cedula,nombre_completo="Invitado de prueba",fecha_visita=timezone.localdate(),instalacion=self.facility,relacion=self.relation);data.update(changes);return data
    def test_writes_two_tables_composite_key(self):
        visit=register_guest(self.user,self.data())
        self.assertEqual(visit.pk,(self.user.pk,"808880888",timezone.localdate(),self.facility.pk))
        self.assertEqual(Guest.objects.count(),1);self.assertEqual(GuestVisit.objects.count(),1)
    def test_duplicate_same_day_facility_rejected(self):
        register_guest(self.user,self.data())
        with self.assertRaises(ValidationError):register_guest(self.user,self.data())
    def test_same_guest_other_facility_allowed_by_schema(self):
        register_guest(self.user,self.data())
        other=Instalacion.objects.create(codigo="PISCINA-2",nombre="Piscina 2",tipo_id="PISCINA",aforo_maximo=20,hora_apertura=time(6),hora_cierre=time(20))
        register_guest(self.user,self.data(instalacion=other))
        self.assertEqual(Guest.objects.count(),1);self.assertEqual(GuestVisit.objects.count(),2)
    def test_limit_and_next_month(self):
        for i in range(4):register_guest(self.user,self.data(f"90000000{i}"))
        with self.assertRaises(ValidationError):register_guest(self.user,self.data())
        nextmonth=(timezone.localdate().replace(day=1)+timedelta(days=32)).replace(day=1)
        register_guest(self.user,self.data(fecha_visita=nextmonth));self.assertEqual(GuestVisit.objects.count(),5)
    def test_cannot_overwrite_existing_guest_identity(self):
        register_guest(self.user,self.data())
        with self.assertRaises(ValidationError):register_guest(self.user,self.data(nombre_completo="Otra persona",fecha_visita=timezone.localdate()+timedelta(days=1)))
        self.assertEqual(Guest.objects.get().nombre_completo,"Invitado de prueba")
    def test_visit_dates_membership_and_facility(self):
        for day in [timezone.localdate()-timedelta(days=1),self.membership.fecha_renovacion+timedelta(days=1)]:
            with self.assertRaises(ValidationError):register_guest(self.user,self.data(fecha_visita=day))
        Instalacion.objects.filter(pk=self.facility.pk).update(activa=False)
        with self.assertRaises(ValidationError):register_guest(self.user,self.data())
    def test_suspended_membership_rejected(self):
        Membership.objects.filter(pk=self.membership.pk).update(estado="SUSPENDIDA")
        with self.assertRaises(ValidationError):register_guest(self.user,self.data())
    def test_self_invitation_rejected(self):
        with self.assertRaises(ValidationError):register_guest(self.user,self.data(self.user.pk))
    def test_reception_date_filter_and_permissions(self):
        today=register_guest(self.user,self.data());register_guest(self.user,self.data("909990999",fecha_visita=timezone.localdate()+timedelta(days=1)))
        self.client.force_login(self.admin,backend="accounts.backends.AdminBackend")
        response=self.client.get(reverse("invitados:recepcion"),{"fecha":timezone.localdate().isoformat()})
        self.assertEqual(response.status_code,200);self.assertEqual(len(response.context["visitas"]),1)
        response=self.client.post(reverse("invitados:ingreso",args=[today.referencia]))
        self.assertEqual(response.status_code,302);self.assertEqual(GuestEntry.objects.count(),1)
    def test_ingress_single_use_signed_key(self):
        today=register_guest(self.user,self.data());check_in(today.referencia)
        self.assertIsNotNone(today.ingreso)
        with self.assertRaises(ValidationError):check_in(today.referencia)
        with self.assertRaises(ValidationError):check_in(today.referencia+"tampered")
    def test_ingress_cannot_be_future(self):
        visit=register_guest(self.user,self.data(fecha_visita=timezone.localdate()+timedelta(days=1)))
        with self.assertRaises(ValidationError):check_in(visit.referencia)
    def test_guest_form_post(self):
        self.client.force_login(self.user,backend="accounts.backends.SocioBackend")
        data=self.data();data.update(fecha_visita=timezone.localdate().isoformat(),instalacion=self.facility.pk,relacion=self.relation.pk)
        response=self.client.post(reverse("invitados:mis_invitados"),data)
        self.assertEqual(response.status_code,302);self.assertEqual(GuestVisit.objects.count(),1)
        self.assertEqual(self.client.get(reverse("invitados:mis_invitados")).status_code,200)
