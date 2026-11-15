from datetime import date,timedelta
from django.test import TestCase,override_settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction, IntegrityError
from django.urls import reverse
from django.utils import timezone
from accounts.tests import member,administrator
from accounts.models import User
from .models import Membership,MembershipType,MembershipHistory,Beneficiary,Kinship
from .services import enroll,save_membership,save_beneficiary,save_type,expire_memberships

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MembershipTests(TestCase):
    def setUp(self):
        self.user=member();self.admin=administrator();self.family=MembershipType.objects.get(pk="FAMILIAR")
    def data(self,obj,**changes):
        data={field:getattr(obj,field) for field in ["socio","tipo","fecha_inscripcion","fecha_renovacion","cuota","estado"]}
        data["motivo"]="Prueba de cambio";data.update(changes);return data
    def beneficiary_data(self,cedula="909990999"):
        return dict(cedula=cedula,nombre_completo="Persona beneficiaria",parentesco=Kinship.objects.get(pk="HIJO"),fecha_nacimiento=date(2010,1,1))
    def test_sql_catalog_preserved(self):
        self.assertEqual(self.family.cuota,90000);self.assertEqual(self.family.limite_beneficiarios,5);self.assertEqual(self.family.limite_invitados,8)
    def test_enroll_canonical_pk_and_trigger(self):
        obj=enroll(self.user,"FAMILIAR")
        self.assertEqual(obj.pk,self.user.cedula);self.assertEqual(obj.estado,"ACTIVA")
        self.assertEqual(obj.historial.count(),1);self.assertEqual(obj.historial.get().motivo,"Inscripción del socio")
        with self.assertRaises(ValidationError):enroll(self.user,"INDIVIDUAL")
    def test_multiple_state_changes_one_transaction(self):
        obj=enroll(self.user,"FAMILIAR")
        for state in ["SUSPENDIDA","ACTIVA","BAJA"]:obj=save_membership(self.data(obj,estado=state),self.admin,obj.pk)
        self.assertEqual(obj.historial.count(),4)
        history=obj.historial.first();self.assertEqual(history.actor_id,self.admin.pk);self.assertEqual(history.nuevo,"BAJA");self.assertEqual(history.motivo,"Prueba de cambio")
    def test_unchanged_state_does_not_duplicate_history(self):
        obj=enroll(self.user,"FAMILIAR");save_membership(self.data(obj,cuota=95000),self.admin,obj.pk)
        self.assertEqual(obj.historial.count(),1)
    def test_admin_creation(self):
        obj=Membership(socio=self.user,tipo=self.family,fecha_inscripcion=timezone.localdate(),fecha_renovacion=timezone.localdate()+timedelta(days=365),cuota=self.family.cuota)
        saved=save_membership(self.data(obj),self.admin)
        self.assertEqual(saved.historial.get().actor_id,self.admin.pk)
    def test_inactive_member_cannot_enroll(self):
        User.objects.filter(pk=self.user.pk).update(estado="SUSPENDIDA")
        with self.assertRaises(ValidationError):enroll(self.user,"INDIVIDUAL")
    def test_invalid_dates(self):
        obj=enroll(self.user,"FAMILIAR")
        with self.assertRaises(ValidationError):save_membership(self.data(obj,fecha_renovacion=obj.fecha_inscripcion),self.admin,obj.pk)
    def test_beneficiary_composite_key_edit_and_limit(self):
        obj=enroll(self.user,"FAMILIAR")
        for i in range(5):save_beneficiary(obj.pk,self.beneficiary_data(f"80000000{i}"))
        with self.assertRaises(ValidationError):save_beneficiary(obj.pk,self.beneficiary_data())
        data=self.beneficiary_data("800000000");data["nombre_completo"]="Nombre corregido"
        ben=save_beneficiary(obj.pk,data,"800000000")
        self.assertEqual(ben.pk,(obj.pk,"800000000"));self.assertEqual(obj.beneficiarios.count(),5)
    def test_nonfamily_or_own_beneficiary_rejected(self):
        obj=enroll(self.user,"INDIVIDUAL")
        with self.assertRaises(ValidationError):save_beneficiary(obj.pk,self.beneficiary_data())
        obj=save_membership(self.data(obj,tipo=self.family),self.admin,obj.pk)
        with self.assertRaises(ValidationError):save_beneficiary(obj.pk,self.beneficiary_data(self.user.pk))
    def test_type_downgrade_with_beneficiaries(self):
        obj=enroll(self.user,"FAMILIAR");save_beneficiary(obj.pk,self.beneficiary_data())
        with self.assertRaises(ValidationError):save_membership(self.data(obj,tipo=MembershipType.objects.get(pk="INDIVIDUAL")),self.admin,obj.pk)
        data={field:getattr(self.family,field) for field in ["codigo","nombre","cuota","limite_beneficiarios","limite_invitados"]};data["limite_beneficiarios"]=0
        with self.assertRaises(ValidationError):save_type(data,self.family.pk)
    def test_expiration_uses_sql_trigger(self):
        obj=enroll(self.user,"FAMILIAR")
        Membership.objects.filter(pk=obj.pk).update(fecha_inscripcion=timezone.localdate()-timedelta(days=400),fecha_renovacion=timezone.localdate()-timedelta(days=1))
        self.assertEqual(expire_memberships(),1);obj.refresh_from_db();self.assertEqual(obj.estado,"VENCIDA");self.assertEqual(obj.historial.count(),2)
    def test_beneficiary_access_cannot_confuse_admin_with_same_pk(self):
        obj=enroll(self.user,"FAMILIAR")
        other=administrator(cedula=self.user.pk,email="otheradmin@example.com",role="COBROS")
        self.client.force_login(other,backend="accounts.backends.AdminBackend")
        self.assertEqual(self.client.get(reverse("membresias:beneficiario_nuevo",args=[obj.pk])).status_code,403)
    def test_beneficiary_other_member_cannot_access(self):
        obj=enroll(self.user,"FAMILIAR");other=member("707770777","other@example.com")
        self.client.force_login(other,backend="accounts.backends.SocioBackend")
        self.assertEqual(self.client.get(reverse("membresias:beneficiario_nuevo",args=[obj.pk])).status_code,403)
    def test_pages_with_natural_and_composite_keys(self):
        obj=enroll(self.user,"FAMILIAR");ben=save_beneficiary(obj.pk,self.beneficiary_data())
        self.client.force_login(self.user,backend="accounts.backends.SocioBackend")
        self.assertEqual(self.client.get(reverse("membresias:mi_membresia")).status_code,200)
        self.assertEqual(self.client.get(reverse("membresias:beneficiario_editar",args=[obj.pk,ben.cedula])).status_code,200)
        self.client.force_login(self.admin,backend="accounts.backends.AdminBackend")
        self.assertEqual(self.client.get(reverse("membresias:editar",args=[obj.pk])).status_code,200)
        self.assertEqual(self.client.get(reverse("membresias:tipo_editar",args=["FAMILIAR"])).status_code,200)
    def test_beneficiary_form_post_and_delete(self):
        obj=enroll(self.user,"FAMILIAR");self.client.force_login(self.user,backend="accounts.backends.SocioBackend")
        data=dict(nombre_completo="Hija de prueba",cedula="909990999",parentesco="HIJO",fecha_nacimiento="2010-01-01")
        response=self.client.post(reverse("membresias:beneficiario_nuevo",args=[obj.pk]),data)
        self.assertEqual(response.status_code,302);self.assertEqual(obj.beneficiarios.count(),1)
        self.assertEqual(self.client.post(reverse("membresias:beneficiario_eliminar",args=[obj.pk,"909990999"])).status_code,302)
        self.assertEqual(obj.beneficiarios.count(),0)
    def test_raw_sql_history_single_entry(self):
        obj=enroll(self.user,"FAMILIAR")
        with connection.cursor() as cur:cur.execute("UPDATE membresia SET codigo_estado='SUSPENDIDA' WHERE cedula_socio=%s",[obj.pk])
        self.assertEqual(obj.historial.count(),2)
