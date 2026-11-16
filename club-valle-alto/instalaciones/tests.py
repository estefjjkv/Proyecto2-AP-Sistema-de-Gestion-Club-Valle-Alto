from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.tests import administrator, member
from core.models import CatMotivoBloqueo, CatTipoInstalacion
from memberships.services import enroll
from reservas.models import Reserva
from .forms import InstalacionForm
from .models import BloqueoInstalacion, Instalacion, ServicioAdicional
from .services import crear_bloqueo, guardar_instalacion, ocupacion, reporte_uso


def local(dia, hora):
    return timezone.make_aware(datetime.combine(dia, time(hora)), timezone.get_default_timezone())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class InstalacionTests(TestCase):
    def setUp(self):
        self.user = member()
        self.admin = administrator()
        enroll(self.user, "INDIVIDUAL")
        self.tenis = guardar_instalacion(self.datos())
        self.manana = timezone.localdate() + timedelta(days=1)

    def datos(self, **cambios):
        datos = dict(codigo="TENIS-1", nombre="Cancha de tenis 1", tipo=CatTipoInstalacion.objects.get(pk="TENIS"),
                     aforo_maximo=4, hora_apertura=time(6), hora_cierre=time(21), activa=True)
        datos.update(cambios)
        return datos

    def reservar(self, inicio=10, fin=11, personas=3, estado="PENDIENTE"):
        return Reserva.objects.create(socio_id=self.user.pk, instalacion=self.tenis, fecha=self.manana,
                                      hora_inicio=time(inicio), hora_fin=time(fin), numero_personas=personas, estado_id=estado)

    def bloqueo(self, inicio=9, fin=12):
        return dict(instalacion=self.tenis, inicio=local(self.manana, inicio), fin=local(self.manana, fin),
                    motivo=CatMotivoBloqueo.objects.get(pk="MANTENIMIENTO"), descripcion="Pintura")

    # --- Instalaciones -------------------------------------------------
    def test_formulario_valida_horario(self):
        form = InstalacionForm(data={**self.datos(codigo="x-2", tipo="TENIS"), "hora_apertura": "10:00", "hora_cierre": "09:00"})
        self.assertFalse(form.is_valid())
        self.assertIn("hora_cierre", form.errors)

    def test_no_desactiva_con_reservas_vigentes(self):
        self.reservar()
        with self.assertRaises(ValidationError):
            guardar_instalacion(self.datos(activa=False), "TENIS-1")
        self.assertTrue(Instalacion.objects.get(pk="TENIS-1").activa)

    def test_desactiva_si_reservas_canceladas(self):
        Reserva.objects.filter(pk=self.reservar().pk).update(estado_id="CANCELADA")
        guardar_instalacion(self.datos(activa=False), "TENIS-1")
        self.assertFalse(Instalacion.objects.get(pk="TENIS-1").activa)

    def test_no_reduce_aforo_ni_horario_con_reservas(self):
        self.reservar(personas=3)
        with self.assertRaises(ValidationError):
            guardar_instalacion(self.datos(aforo_maximo=2), "TENIS-1")
        with self.assertRaises(ValidationError):
            guardar_instalacion(self.datos(hora_apertura=time(10, 30)), "TENIS-1")
        guardar_instalacion(self.datos(nombre="Tenis central", aforo_maximo=3), "TENIS-1")
        self.assertEqual(Instalacion.objects.get(pk="TENIS-1").nombre, "Tenis central")

    # --- Bloqueos ------------------------------------------------------
    def test_bloqueo_rechazado_si_choca_con_reserva(self):
        self.reservar()
        with self.assertRaises(ValidationError):
            crear_bloqueo(self.bloqueo(), self.admin)
        self.assertFalse(BloqueoInstalacion.objects.exists())

    def test_bloqueo_permitido_sin_conflicto_e_impide_reservas(self):
        self.reservar(13, 14)
        bloqueo = crear_bloqueo(self.bloqueo(), self.admin)
        self.assertEqual(bloqueo.admin_id, self.admin.pk)
        # Las columnas son hora local del club: el trigger de reserva debe ver el bloqueo.
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.reservar(10, 11)

    def test_bloqueos_traslapados(self):
        crear_bloqueo(self.bloqueo(9, 12), self.admin)
        with self.assertRaises(ValidationError):
            crear_bloqueo(self.bloqueo(11, 13), self.admin)
        crear_bloqueo(self.bloqueo(12, 13), self.admin)
        self.assertEqual(BloqueoInstalacion.objects.count(), 2)

    # --- Ocupación y reportes -------------------------------------------
    def test_ocupacion_por_franja(self):
        self.reservar(10, 11, personas=3)
        fila = next(f for f in ocupacion(self.manana, time(10), time(11)) if f["instalacion"].pk == "TENIS-1")
        self.assertEqual((fila["personas"], fila["porcentaje"]), (3, 75))
        fila = next(f for f in ocupacion(self.manana, time(11), time(12)) if f["instalacion"].pk == "TENIS-1")
        self.assertEqual(fila["personas"], 0)

    def test_reporte_cuenta_confirmadas(self):
        self.reservar(8, 9, estado="CONFIRMADA")
        self.reservar(10, 11)  # pendiente: no cuenta
        guardar_instalacion(self.datos(codigo="PISCINA-A", nombre="Piscina", tipo=CatTipoInstalacion.objects.get(pk="PISCINA"), aforo_maximo=40))
        reporte = reporte_uso(self.manana.replace(day=1))
        self.assertEqual(reporte["total"], 1)
        self.assertEqual(reporte["mayor"].pk, "TENIS-1")
        self.assertEqual(reporte["menor"].pk, "PISCINA-A")

    # --- Vistas y permisos ---------------------------------------------
    def test_catalogo_socio(self):
        ServicioAdicional.objects.create(codigo="RAQ", nombre="Alquiler de raquetas", tipo_instalacion_id="TENIS", precio=2500)
        self.client.force_login(self.user, backend="accounts.backends.SocioBackend")
        respuesta = self.client.get(reverse("instalaciones:catalogo"))
        self.assertContains(respuesta, "Cancha de tenis 1")
        self.assertContains(respuesta, "Alquiler de raquetas")
        self.assertEqual(self.client.get(reverse("instalaciones:gestion")).status_code, 403)

    def test_pantallas_admin(self):
        self.client.force_login(self.admin, backend="accounts.backends.AdminBackend")
        for nombre in ("gestion", "nueva", "servicios", "bloqueos", "ocupacion", "reportes"):
            self.assertEqual(self.client.get(reverse("instalaciones:" + nombre)).status_code, 200, nombre)
        self.assertEqual(self.client.get(reverse("instalaciones:catalogo")).status_code, 403)

    def test_admin_sin_permiso(self):
        cobros = administrator(cedula="303330333", email="cobros@example.com", role="COBROS")
        self.client.force_login(cobros, backend="accounts.backends.AdminBackend")
        self.assertEqual(self.client.get(reverse("instalaciones:gestion")).status_code, 403)

    def test_admin_registra_y_quita_bloqueo(self):
        self.client.force_login(self.admin, backend="accounts.backends.AdminBackend")
        datos = {"instalacion": "TENIS-1", "fecha_inicio": self.manana, "hora_inicio": "09:00",
                 "fecha_fin": self.manana, "hora_fin": "12:00", "motivo": "MANTENIMIENTO"}
        self.assertRedirects(self.client.post(reverse("instalaciones:bloqueos"), datos), reverse("instalaciones:bloqueos"))
        bloqueo = BloqueoInstalacion.objects.get()
        self.assertEqual(timezone.localtime(bloqueo.inicio).hour, 9)
        self.client.post(reverse("instalaciones:bloqueo_eliminar", args=[bloqueo.pk]))
        self.assertFalse(BloqueoInstalacion.objects.exists())

    def test_admin_crea_instalacion(self):
        self.client.force_login(self.admin, backend="accounts.backends.AdminBackend")
        datos = {"codigo": "golf-1", "nombre": "Golf", "tipo": "GOLF", "aforo_maximo": 8,
                 "hora_apertura": "06:00", "hora_cierre": "18:00", "activa": "on"}
        self.assertRedirects(self.client.post(reverse("instalaciones:nueva"), datos), reverse("instalaciones:gestion"))
        self.assertTrue(Instalacion.objects.filter(pk="GOLF-1", activa=True).exists())
