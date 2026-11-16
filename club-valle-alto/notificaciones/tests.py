from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.tests import administrator, member, registration_data
from .forms import PlantillaForm
from .models import Notificacion, PlantillaNotificacion
from .services import notificar


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class NotificarTests(TestCase):
    def setUp(self):
        self.user = member()
        PlantillaNotificacion.objects.filter(pk="RESERVA_CONFIRMADA").update(
            asunto="Reserva lista, {{nombre}}", cuerpo="Hola {{nombre}}: {{detalle}}.")

    def test_registra_y_envia_al_confirmar(self):
        with self.captureOnCommitCallbacks(execute=True):
            notificacion = notificar(self.user, "RESERVA_CONFIRMADA", detalle="Tenis 10:00")
            self.assertEqual(len(mail.outbox), 0)  # nada se envía antes del commit
        notificacion.refresh_from_db()
        self.assertEqual(notificacion.estado_id, "ENVIADA")
        self.assertIsNotNone(notificacion.fecha_envio)
        self.assertEqual(mail.outbox[0].subject, "Reserva lista, Socio de prueba")
        self.assertEqual(mail.outbox[0].body, "Hola Socio de prueba: Tenis 10:00.")
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_fallo_de_correo_queda_registrado(self):
        with mock.patch("notificaciones.services.send_mail", side_effect=OSError("SMTP caído")), \
                self.assertLogs("notificaciones.services", "ERROR"), \
                self.captureOnCommitCallbacks(execute=True):
            notificacion = notificar(self.user, "PAGO_VENCIDO", detalle="Cuota de octubre")
        notificacion.refresh_from_db()
        self.assertEqual(notificacion.estado_id, "FALLIDA")
        self.assertEqual(Notificacion.objects.count(), 1)



@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CentroNotificacionesTests(TestCase):
    def setUp(self):
        self.user = member()
        self.admin = administrator()
        with self.captureOnCommitCallbacks(execute=True):
            notificar(self.user, "RESERVA_CONFIRMADA", detalle="Tenis 10:00")
        with mock.patch("notificaciones.services.send_mail", side_effect=OSError), \
                self.assertLogs("notificaciones.services", "ERROR"), self.captureOnCommitCallbacks(execute=True):
            self.fallida = notificar(self.user, "PAGO_VENCIDO", detalle="Cuota")

    def entrar(self, rol="GENERAL"):
        cedulas = {"COBROS": "303330333", "INSTALACIONES": "606660666"}
        admin = self.admin if rol == "GENERAL" else administrator(cedula=cedulas[rol], email=f"{rol.lower()}@example.com", role=rol)
        self.client.force_login(admin, backend="accounts.backends.AdminBackend")

    def test_historial_y_filtros(self):
        self.entrar()
        respuesta = self.client.get(reverse("notificaciones:centro"))
        self.assertContains(respuesta, "Tenis 10:00")
        self.assertContains(respuesta, "Editar plantillas")
        fallidas = self.client.get(reverse("notificaciones:centro"), {"estado": "FALLIDA"})
        self.assertContains(fallidas, "Cuota")
        self.assertNotContains(fallidas, "Tenis 10:00")
        por_tipo = self.client.get(reverse("notificaciones:centro"), {"tipo": "RESERVA_CONFIRMADA", "q": "socio@"})
        self.assertContains(por_tipo, "Tenis 10:00")

    def test_reenviar_fallida(self):
        self.entrar()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("notificaciones:reenviar", args=[self.fallida.pk]), {"volver": "https://otro-sitio.com/"})
        self.fallida.refresh_from_db()
        self.assertEqual(self.fallida.estado_id, "ENVIADA")

    def test_editar_plantilla(self):
        self.entrar()
        url = reverse("notificaciones:plantilla", args=["RESERVA_CONFIRMADA"])
        self.assertContains(self.client.get(url), "Vista previa")
        self.assertRedirects(self.client.post(url, {"asunto": "Reserva lista", "cuerpo": "Hola {{ nombre }}: {{detalle}}"}),
                             reverse("notificaciones:centro"))
        plantilla = PlantillaNotificacion.objects.get(pk="RESERVA_CONFIRMADA")
        self.assertEqual((plantilla.cuerpo, plantilla.admin_id), ("Hola {{nombre}}: {{detalle}}", self.admin.pk))
        with self.captureOnCommitCallbacks(execute=True):
            notificar(self.user, "RESERVA_CONFIRMADA", detalle="Golf")
        self.assertEqual(mail.outbox[-1].body, "Hola Socio de prueba: Golf")

    def test_marcadores_desconocidos(self):
        form = PlantillaForm({"asunto": "Hola", "cuerpo": "Hola {{socio}} {{fecha}}"},
                             instance=PlantillaNotificacion.objects.get(pk="NUEVO_SOCIO"))
        self.assertFalse(form.is_valid())
        self.assertIn("{{fecha}}", str(form.errors["cuerpo"]))

    def test_permisos(self):
        self.entrar("COBROS")  # consulta notificaciones, pero no edita plantillas
        self.assertNotContains(self.client.get(reverse("notificaciones:centro")), "Editar plantillas")
        self.assertEqual(self.client.get(reverse("notificaciones:plantilla", args=["NUEVO_SOCIO"])).status_code, 403)
        self.entrar("INSTALACIONES")
        self.assertEqual(self.client.get(reverse("notificaciones:centro")).status_code, 403)

    def test_registro_de_socio_envia_bienvenida(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("socios:registro"), registration_data())
        notificacion = Notificacion.objects.get(tipo_id="NUEVO_SOCIO")
        self.assertEqual((notificacion.correo_destino, notificacion.estado_id), ("nuevo@example.com", "ENVIADA"))
