from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings

from accounts.tests import member
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
