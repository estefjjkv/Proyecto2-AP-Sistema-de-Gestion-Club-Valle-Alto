"""Solicitudes simultáneas con conexiones reales independientes a PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import date,time
from uuid import uuid4
from django.test import TransactionTestCase,override_settings
from django.db import connections,close_old_connections
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.utils import timezone
from accounts.tests import member
from memberships.models import MembershipType,Kinship
from memberships.services import enroll,save_beneficiary
from instalaciones.models import Instalacion
from .models import Relation,GuestVisit
from .services import register_guest

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConcurrentTests(TransactionTestCase):
    def setUp(self):
        code=uuid4().hex[:12].upper()
        self.user=member(code,code.lower()+"@example.com")
        self.kind=MembershipType.objects.get(pk="FAMILIAR")
        self.original_limits=(self.kind.limite_beneficiarios,self.kind.limite_invitados)
        MembershipType.objects.filter(pk=self.kind.pk).update(limite_beneficiarios=1,limite_invitados=1)
        self.facility=Instalacion.objects.create(codigo=code,nombre="Concurrencia",tipo_id="PISCINA",aforo_maximo=20,hora_apertura=time(6),hora_cierre=time(20))
    def tearDown(self):
        MembershipType.objects.filter(pk=self.kind.pk).update(limite_beneficiarios=self.original_limits[0],limite_invitados=self.original_limits[1])
    def parallel_requests(self,fn,count=2):
        barrier=Barrier(count)
        def worker(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                fn(index)
                return "guardado"
            except ValidationError:return "rechazado"
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=count) as pool:return list(pool.map(worker,range(count)))
    def test_guest_last_slot(self):
        obj=enroll(self.user,"FAMILIAR");relation=Relation.objects.get(pk="AMIGO")
        def create(index):register_guest(self.user,dict(nombre_completo="Invitado concurrente",cedula="G"+self.user.pk+str(index),fecha_visita=timezone.localdate(),instalacion=self.facility,relacion=relation))
        self.assertEqual(sorted(self.parallel_requests(create)),["guardado","rechazado"])
        self.assertEqual(GuestVisit.objects.filter(socio=self.user).count(),1)
    def test_beneficiary_last_slot(self):
        obj=enroll(self.user,"FAMILIAR");kinship=Kinship.objects.get(pk="HIJO")
        def create(index):save_beneficiary(obj.pk,dict(nombre_completo="Beneficiario concurrente",cedula="B"+self.user.pk+str(index),fecha_nacimiento=date(2010,1,1),parentesco=kinship))
        self.assertEqual(sorted(self.parallel_requests(create)),["guardado","rechazado"])
        self.assertEqual(obj.beneficiarios.count(),1)
    def test_one_membership_per_socio(self):
        self.assertEqual(sorted(self.parallel_requests(lambda index:enroll(self.user,"FAMILIAR"))),["guardado","rechazado"])
    def test_failed_attempts_atomic(self):
        def attempt(index):authenticate(username=self.user.email,password="incorrecta")
        self.parallel_requests(attempt,count=5)
        self.user.refresh_from_db();self.assertEqual(self.user.failed_attempts,5);self.assertIsNotNone(self.user.locked_until)
