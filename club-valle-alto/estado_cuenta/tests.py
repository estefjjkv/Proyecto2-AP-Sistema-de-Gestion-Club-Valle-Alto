from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests import administrator, member
from memberships.models import Membership
from memberships.services import enroll
from notificaciones.models import Notificacion
from .models import Cargo, EstadoCuenta, Pago
from .services import (colones, generar_estados, limite_pago, obtener_estado_cuenta, procesar_recordatorios,
                       registrar_pago)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EstadoCuentaTests(TestCase):
    def setUp(self):
        self.user = member()
        self.otro = member(cedula="404440444", email="otro@example.com")
        self.admin = administrator()
        enroll(self.user, "FAMILIAR")   # cuota 90 000
        enroll(self.otro, "INDIVIDUAL")  # cuota 50 000
        self.periodo = timezone.localdate().replace(day=1)

    def cargo(self, socio, monto=1000, limite=None, periodo=None):
        periodo = periodo or self.periodo
        estado = obtener_estado_cuenta(socio.pk, periodo)
        return Cargo.objects.create(socio_id=socio.pk, periodo=periodo, tipo_id="SERVICIO_ADICIONAL", descripcion="Servicio",
                                    monto=monto, fecha_limite_pago=limite or estado.fecha_limite_pago)

    # --- Generación ----------------------------------------------------
    def test_limite_dia_10_del_mes_siguiente(self):
        self.assertEqual(limite_pago(date(2026, 11, 1)), date(2026, 12, 10))
        self.assertEqual(limite_pago(date(2026, 12, 1)), date(2027, 1, 10))

    def test_generar_cuotas_es_idempotente_y_notifica(self):
        self.assertEqual(generar_estados(self.periodo), 2)
        self.assertEqual(generar_estados(self.periodo), 0)
        cuota = Cargo.objects.get(socio_id=self.user.pk, tipo_id="CUOTA_MEMBRESIA")
        self.assertEqual(cuota.monto, 90000)
        self.assertEqual(cuota.fecha_limite_pago, limite_pago(self.periodo))
        self.assertEqual(Notificacion.objects.filter(tipo_id="NUEVO_ESTADO_CUENTA").count(), 2)

    def test_no_cobra_membresias_no_activas_ni_cuota_cero(self):
        Membership.objects.filter(socio=self.otro).update(estado="SUSPENDIDA")
        honorario = member(cedula="505550555", email="honor@example.com")
        enroll(honorario, "HONORARIA")  # cuota 0
        self.assertEqual(generar_estados(self.periodo), 1)
        self.assertFalse(Cargo.objects.filter(socio_id__in=[self.otro.pk, honorario.pk]).exists())

    def test_no_cobra_meses_fuera_de_vigencia(self):
        anterior = date(self.periodo.year - 1, self.periodo.month, 1)
        self.assertEqual(generar_estados(anterior), 0)

    # --- Pagos ---------------------------------------------------------
    def test_registrar_pago_salda_cargos(self):
        a, b = self.cargo(self.user, 3000), self.cargo(self.user, 2500)
        pago = registrar_pago(self.user.pk, [a, b], timezone.localdate(), " Transferencia 123 ", self.admin)
        self.assertEqual((pago.monto, pago.referencia, pago.admin_id), (Decimal("5500"), "Transferencia 123", self.admin.pk))
        for cargo in Cargo.objects.filter(pk__in=[a.pk, b.pk]):
            self.assertEqual((cargo.estado_id, cargo.admin_pago_id), ("PAGADO", self.admin.pk))
            self.assertIsNotNone(cargo.fecha_pago)
        self.assertEqual(pago.detalles.count(), 2)

    def test_pago_rechazado(self):
        a, ajeno = self.cargo(self.user), self.cargo(self.otro)
        hoy = timezone.localdate()
        casos = {"sin cargos": [], "cargo de otro socio": [a, ajeno]}
        for nombre, cargos in casos.items():
            with self.subTest(nombre), self.assertRaises(ValidationError):
                registrar_pago(self.user.pk, cargos, hoy, "", self.admin)
        with self.assertRaises(ValidationError):
            registrar_pago(self.user.pk, [a], hoy + timedelta(days=1), "", self.admin)
        registrar_pago(self.user.pk, [a], hoy, "", self.admin)
        with self.assertRaises(ValidationError):
            registrar_pago(self.user.pk, [a], hoy, "", self.admin)  # ya pagado
        self.assertEqual(Pago.objects.count(), 1)

    # --- Recordatorios -------------------------------------------------
    def test_recordatorios(self):
        hoy = timezone.localdate()
        vencido = self.cargo(self.user, limite=hoy - timedelta(days=1))
        self.cargo(self.otro, limite=hoy + timedelta(days=3))
        self.cargo(self.otro, limite=hoy + timedelta(days=10))  # todavía no se avisa
        self.assertEqual(procesar_recordatorios(hoy), (1, 1))
        self.assertEqual(Cargo.objects.get(pk=vencido.pk).estado_id, "VENCIDO")
        self.assertEqual(procesar_recordatorios(hoy), (0, 0))  # no repite avisos
        self.assertEqual(Notificacion.objects.get(tipo_id="PAGO_VENCIDO").socio_id, self.user.pk)
        self.assertEqual(Notificacion.objects.get(tipo_id="PAGO_POR_VENCER").socio_id, self.otro.pk)

    # --- Vistas -------------------------------------------------------
    def test_vistas_socio(self):
        generar_estados(self.periodo)
        self.cargo(self.user, 3000)
        self.client.force_login(self.user, backend="accounts.backends.SocioBackend")
        respuesta = self.client.get(reverse("estado_cuenta:mi_estado"))
        self.assertContains(respuesta, colones(93000))
        self.assertContains(respuesta, "Cuota Membresía familiar")
        self.assertEqual(self.client.get(reverse("estado_cuenta:historial")).status_code, 200)
        imprimir = self.client.get(reverse("estado_cuenta:imprimir", args=[self.periodo.strftime("%Y-%m")]))
        self.assertContains(imprimir, self.user.nombre_completo)
        self.assertEqual(self.client.get(reverse("estado_cuenta:imprimir", args=["1999-01"])).status_code, 404)
        self.assertEqual(self.client.get(reverse("estado_cuenta:gestion")).status_code, 403)

    def test_socio_no_ve_cargos_ajenos(self):
        self.cargo(self.otro, 7777)
        self.client.force_login(self.user, backend="accounts.backends.SocioBackend")
        self.assertNotContains(self.client.get(reverse("estado_cuenta:mi_estado") + f"?periodo={self.periodo}"), colones(7777))
        self.assertEqual(self.client.get(reverse("estado_cuenta:imprimir", args=[self.periodo.strftime("%Y-%m")])).status_code, 404)

    def test_vistas_admin(self):
        self.client.force_login(self.admin, backend="accounts.backends.AdminBackend")
        self.client.post(reverse("estado_cuenta:generar"), {"periodo": self.periodo.isoformat()})
        self.assertEqual(EstadoCuenta.objects.filter(periodo=self.periodo).count(), 2)
        lista = self.client.get(reverse("estado_cuenta:gestion"), {"periodo": self.periodo.isoformat(), "q": "Socio"})
        self.assertContains(lista, self.user.pk)
        self.assertEqual(self.client.get(reverse("estado_cuenta:admin_detalle", args=[self.user.pk])).status_code, 200)
        cuota = Cargo.objects.get(socio_id=self.user.pk)
        pagos = self.client.get(reverse("estado_cuenta:pagos"), {"socio": self.user.pk})
        self.assertContains(pagos, cuota.descripcion)
        self.client.post(reverse("estado_cuenta:pagos"), {"socio": self.user.pk, "cargos": [cuota.pk],
                                                          "fecha_pago": timezone.localdate().isoformat(), "referencia": "Caja"})
        self.assertEqual(Cargo.objects.get(pk=cuota.pk).estado_id, "PAGADO")
        pagado = self.client.get(reverse("estado_cuenta:gestion"), {"periodo": self.periodo.isoformat(), "estado": "PAGADO"})
        self.assertContains(pagado, self.user.pk)
        self.assertNotContains(pagado, self.otro.pk)

    def test_admin_sin_permiso_de_cobros(self):
        instalaciones = administrator(cedula="303330333", email="inst@example.com", role="INSTALACIONES")
        self.client.force_login(instalaciones, backend="accounts.backends.AdminBackend")
        self.assertEqual(self.client.get(reverse("estado_cuenta:pagos")).status_code, 403)
