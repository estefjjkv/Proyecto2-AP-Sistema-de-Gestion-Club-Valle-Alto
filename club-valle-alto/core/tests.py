from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import Administrator, User
from estado_cuenta.models import Pago, VSocioMoroso
from guests.models import GuestVisit
from notificaciones.models import Notificacion
from reservas.models import Reserva


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CargarDemoTests(TestCase):
    def test_carga_todos_los_modulos_y_no_duplica(self):
        salida = StringIO()
        with self.captureOnCommitCallbacks(execute=True):
            call_command("cargar_demo", stdout=salida)
        self.assertIn("Datos de demostración cargados", salida.getvalue())
        self.assertEqual(User.objects.filter(email__endswith="@example.com").count(), 5)
        self.assertEqual(Administrator.objects.filter(email__endswith="@example.com").count(), 3)
        estados = set(Reserva.objects.values_list("estado_id", flat=True))
        self.assertEqual(estados, {"PENDIENTE", "CONFIRMADA", "CANCELADA", "FINALIZADA"})
        self.assertEqual(GuestVisit.objects.count(), 3)
        self.assertTrue(Pago.objects.exists())
        self.assertTrue(VSocioMoroso.objects.filter(nombre_completo__startswith="Ana").exists())
        self.assertFalse(Notificacion.objects.exclude(estado_id="ENVIADA").exists())

        reservas = Reserva.objects.count()
        call_command("cargar_demo", stdout=StringIO())
        self.assertEqual(Reserva.objects.count(), reservas)
