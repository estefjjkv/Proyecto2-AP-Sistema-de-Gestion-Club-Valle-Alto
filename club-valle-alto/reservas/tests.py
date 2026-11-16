from datetime import datetime, time, timedelta

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests import administrator, member
from core.models import CatMotivoBloqueo, CatTipoInstalacion
from estado_cuenta.models import Cargo, EstadoCuenta
from instalaciones.models import ServicioAdicional
from instalaciones.services import crear_bloqueo, guardar_instalacion
from memberships.services import enroll
from notificaciones.models import Notificacion
from .models import Reserva, ReservaHistorial
from .services import cancelar_reserva, crear_reserva, disponibilidad, finalizar_reservas, modificar_reserva


def local(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora), timezone.get_default_timezone())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ReservaTests(TestCase):
    def setUp(self):
        self.user = member()
        self.otro = member(cedula="404440444", email="otro@example.com")
        self.admin = administrator()
        enroll(self.user, "INDIVIDUAL")
        enroll(self.otro, "INDIVIDUAL")
        self.tenis = guardar_instalacion(dict(codigo="TENIS-1", nombre="Cancha de tenis", tipo=CatTipoInstalacion.objects.get(pk="TENIS"),
                                              aforo_maximo=4, hora_apertura=time(6), hora_cierre=time(21), activa=True))
        self.raquetas = ServicioAdicional.objects.create(codigo="RAQ", nombre="Raquetas", tipo_instalacion_id="TENIS", precio=3000)
        self.bolas = ServicioAdicional.objects.create(codigo="BOL", nombre="Bolas", tipo_instalacion_id="TENIS", precio=2500)
        self.toallas = ServicioAdicional.objects.create(codigo="TOA", nombre="Toallas", tipo_instalacion_id="PISCINA", precio=1000)
        self.manana = timezone.localdate() + timedelta(days=1)

    def datos(self, inicio=10, fin=11, personas=2, servicios=(), **extra):
        datos = dict(instalacion=self.tenis, fecha=self.manana, hora_inicio=time(inicio), hora_fin=time(fin),
                     numero_personas=personas, servicios=list(servicios))
        datos.update(extra)
        return datos

    def cargo(self, reserva):
        return Cargo.objects.filter(reserva_id=reserva.pk).first()

    # --- Crear ---------------------------------------------------------
    def test_socio_crea_pendiente_con_cargo_e_historial(self):
        reserva = crear_reserva(self.datos(servicios=[self.raquetas, self.bolas]), self.user)
        self.assertEqual(reserva.estado_id, "PENDIENTE")
        self.assertEqual(reserva.servicios.count(), 2)
        cargo = self.cargo(reserva)
        self.assertEqual((cargo.monto, cargo.tipo_id, cargo.periodo), (5500, "SERVICIO_ADICIONAL", self.manana.replace(day=1)))
        estado = EstadoCuenta.objects.get(socio_id=self.user.pk, periodo=self.manana.replace(day=1))
        self.assertEqual(cargo.fecha_limite_pago, estado.fecha_limite_pago)
        self.assertEqual(reserva.historial.get().accion, "CREADA")
        self.assertFalse(Notificacion.objects.exists())  # se avisa al confirmar

    def test_sin_servicios_no_genera_cargo(self):
        self.assertIsNone(self.cargo(crear_reserva(self.datos(), self.user)))

    def test_validaciones(self):
        crear_reserva(self.datos(10, 11), self.user)
        casos = {
            "traslape": self.datos(10, 12),
            "fuera de horario": self.datos(20, 22),
            "aforo": self.datos(12, 13, personas=5),
            "pasado": self.datos(fecha=timezone.localdate() - timedelta(days=1)),
            "servicio de otro tipo": self.datos(12, 13, servicios=[self.toallas]),
        }
        for nombre, datos in casos.items():
            with self.subTest(nombre), self.assertRaises(ValidationError):
                crear_reserva(datos, self.otro)
        crear_reserva(self.datos(11, 12), self.otro)  # contigua: permitida

    def test_bloqueo_y_membresia(self):
        crear_bloqueo(dict(instalacion=self.tenis, inicio=local(self.manana, time(14)), fin=local(self.manana, time(16)),
                           motivo=CatMotivoBloqueo.objects.get(pk="MANTENIMIENTO")), self.admin)
        with self.assertRaises(ValidationError):
            crear_reserva(self.datos(15, 16), self.user)
        sin_membresia = member(cedula="505550555", email="sin@example.com")
        with self.assertRaises(ValidationError):
            crear_reserva(self.datos(), sin_membresia)

    def test_admin_crea_confirmada_y_notifica(self):
        with self.captureOnCommitCallbacks(execute=True):
            reserva = crear_reserva(self.datos(socio=self.user), self.admin)
        self.assertEqual((reserva.estado_id, reserva.admin_id), ("CONFIRMADA", self.admin.pk))
        self.assertEqual(Notificacion.objects.get().tipo_id, "RESERVA_CONFIRMADA")
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    # --- Modificar y confirmar -----------------------------------------
    def test_admin_confirma(self):
        reserva = crear_reserva(self.datos(), self.user)
        with self.captureOnCommitCallbacks(execute=True):
            reserva = modificar_reserva(reserva.pk, self.datos(), self.admin, confirmar=True)
        self.assertEqual(reserva.estado_id, "CONFIRMADA")
        self.assertEqual(list(reserva.historial.values_list("accion", flat=True)), ["CONFIRMADA", "CREADA"])
        self.assertEqual(len(mail.outbox), 1)

    def test_socio_modifica_y_vuelve_a_pendiente(self):
        reserva = crear_reserva(self.datos(servicios=[self.raquetas]), self.user)
        modificar_reserva(reserva.pk, self.datos(), self.admin, confirmar=True)
        reserva = modificar_reserva(reserva.pk, self.datos(12, 14, servicios=[self.bolas]), self.user)
        self.assertEqual((reserva.estado_id, reserva.hora_inicio), ("PENDIENTE", time(12)))
        self.assertEqual(self.cargo(reserva).monto, 2500)
        self.assertIn("hora de inicio", reserva.historial.first().detalle)
        reserva = modificar_reserva(reserva.pk, self.datos(12, 14), self.user)
        self.assertIsNone(self.cargo(reserva))

    def test_modificar_no_choca_consigo_misma(self):
        reserva = crear_reserva(self.datos(10, 12), self.user)
        modificar_reserva(reserva.pk, self.datos(11, 13), self.user)  # se traslapa solo con su propio horario anterior

    def test_cargo_pagado_no_se_cambia(self):
        reserva = crear_reserva(self.datos(servicios=[self.raquetas]), self.user)
        Cargo.objects.filter(reserva_id=reserva.pk).update(estado_id="PAGADO", fecha_pago=timezone.now())
        with self.assertRaises(ValidationError):
            modificar_reserva(reserva.pk, self.datos(servicios=[self.bolas]), self.user)
        modificar_reserva(reserva.pk, self.datos(12, 13, servicios=[self.raquetas]), self.user)  # mismo mes y servicios
        cancelar_reserva(reserva.pk, self.user)
        self.assertEqual(self.cargo(reserva).estado_id, "PAGADO")

    def test_socio_no_modifica_ajena_ni_confirma(self):
        reserva = crear_reserva(self.datos(), self.user)
        with self.assertRaises(ValidationError):
            modificar_reserva(reserva.pk, self.datos(12, 13), self.otro)
        with self.assertRaises(ValidationError):
            modificar_reserva(reserva.pk, self.datos(), self.user, confirmar=True)

    # --- Cancelar y finalizar ------------------------------------------
    def test_cancelar_borra_cargo_y_notifica(self):
        reserva = crear_reserva(self.datos(servicios=[self.raquetas]), self.user)
        with self.captureOnCommitCallbacks(execute=True):
            reserva = cancelar_reserva(reserva.pk, self.admin, "Lluvia")
        self.assertEqual(reserva.estado_id, "CANCELADA")
        self.assertIsNotNone(reserva.fecha_cancelacion)
        self.assertIsNone(self.cargo(reserva))
        self.assertIn("Motivo: Lluvia", mail.outbox[0].body)
        crear_reserva(self.datos(), self.otro)  # el horario quedó libre
        with self.assertRaises(ValidationError):
            cancelar_reserva(reserva.pk, self.user)

    def test_finalizar_reservas(self):
        confirmada = crear_reserva(self.datos(8, 9, socio=self.user), self.admin)
        pendiente = crear_reserva(self.datos(10, 11), self.otro)
        futura = crear_reserva(self.datos(15, 16), self.user)
        resultado = finalizar_reservas(local(self.manana, time(12)))
        self.assertEqual(resultado, (1, 1))
        self.assertEqual(Reserva.objects.get(pk=confirmada.pk).estado_id, "FINALIZADA")
        self.assertEqual(Reserva.objects.get(pk=pendiente.pk).estado_id, "CANCELADA")
        self.assertEqual(Reserva.objects.get(pk=futura.pk).estado_id, "PENDIENTE")
        self.assertEqual(ReservaHistorial.objects.filter(actor_tipo="SISTEMA").count(), 2)

    # --- Disponibilidad -----------------------------------------------
    def test_disponibilidad(self):
        crear_reserva(self.datos(10, 11), self.user)
        crear_reserva(self.datos(12, 13, socio=self.otro), self.admin)
        franjas = [(f["inicio"], f["fin"], f["estado"]) for f in disponibilidad(self.tenis, self.manana)]
        self.assertEqual(franjas, [("06:00", "10:00", "libre"), ("10:00", "11:00", "pendiente"), ("11:00", "12:00", "libre"),
                                   ("12:00", "13:00", "ocupado"), ("13:00", "21:00", "libre")])

    # --- Vistas -------------------------------------------------------
    def test_flujo_socio_en_vistas(self):
        self.client.force_login(self.user, backend="accounts.backends.SocioBackend")
        self.assertEqual(self.client.get(reverse("reservas:nueva") + "?instalacion=TENIS-1").status_code, 200)
        respuesta = self.client.post(reverse("reservas:nueva"), {
            "instalacion": "TENIS-1", "fecha": self.manana.isoformat(), "hora_inicio": "10:00", "hora_fin": "11:00",
            "numero_personas": 2, "servicios": ["RAQ"]})
        reserva = Reserva.objects.get()
        self.assertRedirects(respuesta, reverse("reservas:detalle", args=[reserva.pk]))
        self.assertContains(self.client.get(reverse("reservas:mis_reservas")), "Cancha de tenis")
        self.assertContains(self.client.get(reverse("reservas:detalle", args=[reserva.pk])), "Raquetas")
        self.assertEqual(self.client.get(reverse("reservas:modificar", args=[reserva.pk])).status_code, 200)
        json = self.client.get(reverse("reservas:disponibilidad"), {"instalacion": "TENIS-1", "fecha": self.manana.isoformat()}).json()
        self.assertIn("pendiente", [f["estado"] for f in json["franjas"]])
        self.client.post(reverse("reservas:cancelar", args=[reserva.pk]))
        self.assertEqual(Reserva.objects.get().estado_id, "CANCELADA")
        # Pantallas de administración, prohibidas para el socio
        self.assertEqual(self.client.get(reverse("reservas:calendario")).status_code, 403)

    def test_socio_no_ve_reserva_ajena(self):
        reserva = crear_reserva(self.datos(), self.otro)
        self.client.force_login(self.user, backend="accounts.backends.SocioBackend")
        self.assertEqual(self.client.get(reverse("reservas:detalle", args=[reserva.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("reservas:cancelar", args=[reserva.pk])).status_code, 404)

    def test_flujo_admin_en_vistas(self):
        pendiente = crear_reserva(self.datos(), self.user)
        self.client.force_login(self.admin, backend="accounts.backends.AdminBackend")
        calendario = self.client.get(reverse("reservas:calendario"), {"semana": self.manana.isoformat()})
        self.assertContains(calendario, "Socio de prueba")
        self.assertEqual(self.client.get(reverse("reservas:admin_nueva")).status_code, 200)
        self.assertContains(self.client.get(reverse("reservas:administrar", args=[pendiente.pk])), "Confirmar reserva")
        datos = {"instalacion": "TENIS-1", "fecha": self.manana.isoformat(), "hora_inicio": "10:00", "hora_fin": "11:00",
                 "numero_personas": 3, "accion": "confirmar"}
        self.client.post(reverse("reservas:administrar", args=[pendiente.pk]), datos)
        pendiente.refresh_from_db()
        self.assertEqual((pendiente.estado_id, pendiente.numero_personas), ("CONFIRMADA", 3))
        respuesta = self.client.post(reverse("reservas:admin_nueva"), {**datos, "socio": self.otro.pk, "hora_inicio": "12:00", "hora_fin": "13:00"})
        nueva = Reserva.objects.exclude(pk=pendiente.pk).get()
        self.assertRedirects(respuesta, reverse("reservas:administrar", args=[nueva.pk]))
        self.client.post(reverse("reservas:admin_cancelar", args=[nueva.pk]), {"motivo": "Prueba"})
        self.assertEqual(Reserva.objects.get(pk=nueva.pk).estado_id, "CANCELADA")
