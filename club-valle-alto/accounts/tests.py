import hashlib
import re
from datetime import date, timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings, Client
from django.contrib.auth import authenticate
from django.core import mail
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from .models import User, Administrator, AdminRole, RolePermission, RecoveryToken, AccountEvent
from .forms import RegistroSocioForm, PerfilForm
from .services import send_password_reset, complete_reset, get_reset_user, set_member_state

PASSWORD="Faro!Bosque729!"

def member(cedula="101110111", email="socio@example.com"):
    return User.objects.create_user(email, PASSWORD, cedula=cedula, nombre_completo="Socio de prueba",telefono="88887777",direccion="San José",fecha_nacimiento=date(1995,1,10))

def administrator(cedula="202220222", email="admin@example.com", role="GENERAL"):
    return Administrator.objects.create_user(email,PASSWORD,cedula=cedula,nombre_completo="Administración de prueba",rol=AdminRole.objects.get(pk=role))

def registration_data(**changes):
    data=dict(nombre_completo="Nueva Persona",cedula="303330333",email="nuevo@example.com",telefono="8888-7777",direccion="Heredia",fecha_nacimiento="1997-06-10",password1=PASSWORD,password2=PASSWORD)
    data.update(changes);return data

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AccountTests(TestCase):
    def setUp(self):
        self.socio=member();self.admin=administrator()
    def login(self,admin=False):
        self.client.force_login(self.admin if admin else self.socio,backend="accounts.backends.AdminBackend" if admin else "accounts.backends.SocioBackend")
    def test_register_writes_canonical_table_and_hash(self):
        response=self.client.post(reverse("socios:registro"),registration_data())
        self.assertEqual(response.status_code,302)
        with connection.cursor() as cursor:
            cursor.execute("SELECT cedula,correo,password_hash,telefono,codigo_estado FROM socio WHERE correo=%s",["nuevo@example.com"])
            row=cursor.fetchone()
        self.assertEqual(row[0],"303330333");self.assertNotEqual(row[2],PASSWORD);self.assertEqual(row[4],"ACTIVA")
        self.assertTrue(User.objects.get(pk=row[0]).check_password(PASSWORD))
        self.assertEqual(Administrator.objects.count(),1)
    def test_invalid_registration(self):
        for field,value in [("email","invalid"),("cedula","12"),("telefono","123"),("fecha_nacimiento",timezone.localdate().isoformat()),("password2","incorrecta")]:
            form=RegistroSocioForm(registration_data(**{field:value}));self.assertFalse(form.is_valid(),field)
    def test_duplicate_email_case_insensitive(self):
        self.assertFalse(RegistroSocioForm(registration_data(email="SOCIO@EXAMPLE.COM")).is_valid())
    def test_login_socios_and_admins_same_key_email(self):
        other=administrator(cedula=self.socio.pk,email=self.socio.email)
        for kind,cls in [("socio",User),("administrador",Administrator)]:
            result=authenticate(username=self.socio.email,password=PASSWORD,cuenta=kind)
            self.assertIsInstance(result,cls)
            response=self.client.post(reverse("usuarios:login"),dict(username=self.socio.email,password=PASSWORD,cuenta=kind))
            self.assertEqual(response.status_code,302)
            self.assertEqual(self.client.get(response.url).status_code,200)
            self.client.logout()
    def test_lockout_and_expiry(self):
        for _ in range(5):self.assertIsNone(authenticate(username=self.socio.email,password="incorrecta"))
        self.socio.refresh_from_db();self.assertEqual(self.socio.failed_attempts,5);self.assertIsNotNone(self.socio.locked_until)
        self.assertIsNone(authenticate(username=self.socio.email,password=PASSWORD))
        User.objects.filter(pk=self.socio.pk).update(locked_until=timezone.now()-timedelta(seconds=1))
        self.assertIsNotNone(authenticate(username=self.socio.email,password=PASSWORD))
        self.socio.refresh_from_db();self.assertEqual(self.socio.failed_attempts,0)
    def test_admin_lockout_separate(self):
        same=administrator(cedula=self.socio.pk,email=self.socio.email)
        for _ in range(5):authenticate(username=self.socio.email,password="wrong",cuenta="administrador")
        self.assertIsNotNone(authenticate(username=self.socio.email,password=PASSWORD,cuenta="socio"))
        self.assertIsNone(authenticate(username=self.socio.email,password=PASSWORD,cuenta="administrador"))
    def test_suspend_invalidates_existing_session(self):
        self.login();set_member_state(self.socio.pk,"SUSPENDIDA",self.admin)
        self.assertEqual(self.client.get(reverse("socios:inicio")).status_code,302)
        self.assertIsNone(authenticate(username=self.socio.email,password=PASSWORD))
    def test_state_enum_and_audit(self):
        with self.assertRaises(ValidationError):set_member_state(self.socio.pk,"activa",self.admin)
        set_member_state(self.socio.pk,"DESACTIVADA",self.admin)
        self.assertTrue(AccountEvent.objects.filter(target_id=self.socio.pk,target_kind="socio").exists())
    def test_profile_cannot_change_primary_key(self):
        data=registration_data(cedula="999990999",email=self.socio.email)
        form=PerfilForm(data,instance=self.socio)
        self.assertTrue(form.is_valid(),form.errors);form.save()
        self.assertTrue(User.objects.filter(pk="101110111").exists());self.assertFalse(User.objects.filter(pk="999990999").exists())
    def test_permissions_follow_sql_role_permission(self):
        self.assertTrue(self.admin.has_perm("accounts.manage_members"))
        RolePermission.objects.filter(codigo_rol="GENERAL",codigo_permiso="GESTIONAR_SOCIOS").delete()
        self.assertFalse(self.admin.has_perm("accounts.manage_members"))
    def test_role_restrictions(self):
        self.login();self.assertEqual(self.client.get(reverse("socios:gestion")).status_code,403)
        admin=administrator("404440444","cobros@example.com","COBROS")
        self.client.force_login(admin,backend="accounts.backends.AdminBackend")
        self.assertEqual(self.client.get(reverse("administradores:gestion")).status_code,403)
        self.assertEqual(self.client.get(reverse("invitados:recepcion")).status_code,403)
    def test_admin_can_create_without_creating_socio(self):
        self.login(True)
        data=registration_data(cedula="505550555",email="nuevoadmin@example.com",rol="INSTALACIONES")
        response=self.client.post(reverse("administradores:gestion"),data)
        self.assertEqual(response.status_code,302)
        self.assertTrue(Administrator.objects.get(pk=data["cedula"]).check_password(PASSWORD))
        self.assertFalse(User.objects.filter(pk=data["cedula"]).exists())
    def test_admin_cannot_remove_own_access(self):
        self.login(True)
        response=self.client.post(reverse("administradores:editar",args=[self.admin.pk]),dict(nombre_completo=self.admin.nombre_completo,cedula=self.admin.pk,email=self.admin.email,rol="COBROS",activo="on"))
        self.assertEqual(response.status_code,200);self.admin.refresh_from_db();self.assertEqual(self.admin.rol_id,"GENERAL")
    def test_recovery_hash_single_use_and_all_links_invalidated(self):
        for _ in range(2):self.assertTrue(send_password_reset(self.socio.email))
        raw=re.search(r"restablecer/([^/]+)/",mail.outbox[-1].body)[1]
        self.assertTrue(RecoveryToken.objects.filter(pk=hashlib.sha256(raw.encode()).hexdigest()).exists())
        self.assertFalse(RecoveryToken.objects.filter(pk=raw).exists())
        complete_reset(raw,"Nuevo!Faro898!");self.assertIsNone(get_reset_user(raw));self.assertFalse(RecoveryToken.objects.filter(usado=False).exists())
        self.socio.refresh_from_db();self.assertTrue(self.socio.check_password("Nuevo!Faro898!"))
        with self.assertRaises(ValidationError):complete_reset(raw,"Otro!Faro789!")
    def test_reset_expired_or_suspended(self):
        send_password_reset(self.socio.email);raw=re.search(r"restablecer/([^/]+)/",mail.outbox[-1].body)[1]
        RecoveryToken.objects.update(fecha_expira=timezone.now()-timedelta(seconds=1));self.assertIsNone(get_reset_user(raw))
        with self.assertRaises(ValidationError):complete_reset(raw,PASSWORD)
    def test_reset_unknown_does_not_reveal_account(self):
        self.assertTrue(send_password_reset("unknown@example.com"));self.assertEqual(len(mail.outbox),0)
    def test_smtp_failure_removes_token(self):
        with patch("accounts.services.send_mail",side_effect=OSError):self.assertFalse(send_password_reset(self.socio.email))
        self.assertFalse(RecoveryToken.objects.exists())
    def test_reset_browser_flow(self):
        send_password_reset(self.socio.email);raw=re.search(r"restablecer/([^/]+)/",mail.outbox[-1].body)[1]
        response=self.client.get(reverse("usuarios:reset_confirm",args=[raw]));self.assertEqual(response.status_code,302)
        response=self.client.post(response.url,{"new_password1":"Nuevo!Clave456", "new_password2":"Nuevo!Clave456"})
        self.assertRedirects(response,reverse("usuarios:reset_complete"))
    def test_logout_post_only_and_csrf(self):
        self.login();self.assertEqual(self.client.get(reverse("usuarios:salir")).status_code,405)
        csrf=Client(enforce_csrf_checks=True)
        self.assertEqual(csrf.post(reverse("socios:registro"),registration_data()).status_code,403)
        self.assertEqual(self.client.post(reverse("usuarios:salir")).status_code,302)
    def test_all_pages_render(self):
        for name in ["usuarios:login","usuarios:recuperar","socios:registro"]:self.assertEqual(self.client.get(reverse(name)).status_code,200,name)
        self.login()
        for name in ["socios:inicio","socios:perfil","membresias:mi_membresia","invitados:mis_invitados"]:self.assertEqual(self.client.get(reverse(name)).status_code,200,name)
        self.client.logout();self.login(True)
        for name in ["administradores:panel","administradores:gestion","socios:gestion","membresias:gestion","membresias:formulario","membresias:tipos","invitados:recepcion"]:self.assertEqual(self.client.get(reverse(name)).status_code,200,name)
        self.assertEqual(self.client.get(reverse("socios:gestion_detalle",args=[self.socio.pk])).status_code,200)
    def test_prototype_routes_guarded(self):
        self.assertEqual(self.client.get("/reservas/calendario/").status_code,302)
        self.login();self.assertEqual(self.client.get("/reservas/calendario/").status_code,403)
    def test_admin_password_reset_and_keep_own_session(self):
        self.login(True)
        response=self.client.post(reverse("administradores:clave",args=[self.admin.pk]),{"new_password1":"Cambio!Seguro389", "new_password2":"Cambio!Seguro389"})
        self.assertEqual(response.status_code,302);self.admin.refresh_from_db();self.assertTrue(self.admin.check_password("Cambio!Seguro389"))
        self.assertEqual(self.client.get(reverse("administradores:gestion")).status_code,200)
        self.assertEqual(AccountEvent.objects.get(action="Contraseña administrativa restablecida").actor_kind,"administrador")
    def test_member_cannot_reset_administrator(self):
        self.login();self.assertEqual(self.client.post(reverse("administradores:clave",args=[self.admin.pk]),{}).status_code,403)
    def test_admin_deactivation_revokes_session(self):
        self.login(True);Administrator.objects.filter(pk=self.admin.pk).update(activo=False)
        self.assertEqual(self.client.get(reverse("administradores:gestion")).status_code,302)
    def test_registration_cannot_grant_privileges(self):
        self.client.post(reverse("socios:registro"),registration_data(rol="GENERAL",is_superuser="on",is_staff="on"))
        new=User.objects.get(email="nuevo@example.com");self.assertFalse(new.has_perm("accounts.manage_members"));self.assertFalse(new.is_staff)
    def test_import_refuses_existing_database(self):
        from django.core.management import call_command,CommandError
        with self.assertRaises(CommandError):call_command("importar_sql")
        self.assertEqual(User.objects.count(),1)
    def test_required_columns_match_sql(self):
        from django.core.management import call_command
        from io import StringIO
        call_command("verificar_base",stdout=StringIO())
