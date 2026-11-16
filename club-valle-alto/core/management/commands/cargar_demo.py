"""
Carga un conjunto de datos de demostración que recorre todos los módulos.

    python manage.py cargar_demo

Usa los mismos servicios que las pantallas, así que los datos cumplen las
reglas del sistema (triggers, cargos, historial y notificaciones). Las fechas
se calculan a partir de hoy, para que siempre haya reservas futuras, cargos
vencidos e invitados esperados. Si los datos ya existen, no hace nada.

Los correos de demostración no se envían de verdad: se registran en el
historial de notificaciones como enviados.
"""
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.test import override_settings
from django.utils import timezone

from accounts.models import AdminRole, Administrator, User
from core.models import CatMotivoBloqueo
from estado_cuenta.models import Cargo
from estado_cuenta.services import generar_estados, procesar_recordatorios, registrar_pago
from guests.models import Relation
from guests.services import register_guest
from instalaciones.models import Instalacion, ServicioAdicional
from instalaciones.services import crear_bloqueo
from memberships.models import Kinship, Membership
from memberships.services import enroll, save_beneficiary
from reservas.models import Reserva, ReservaHistorial
from reservas.services import cancelar_reserva, crear_reserva, modificar_reserva

CLAVE = "ClubDemo2026!"

INSTALACIONES = [
    # código, nombre, tipo, aforo, apertura, cierre
    ("TENIS-1", "Cancha de tenis", "TENIS", 4, 6, 21),
    ("GOLF-1", "Campo de golf", "GOLF", 8, 6, 18),
    ("PISCINA-1", "Piscina", "PISCINA", 40, 7, 20),
    ("SALON-1", "Salón de eventos", "SALON_EVENTOS", 120, 10, 23),
]
SERVICIOS = [
    ("RAQUETAS", "Alquiler de raquetas", "TENIS", 3000),
    ("BOLAS", "Tubo de bolas", "TENIS", 2500),
    ("CARRITO", "Alquiler de carrito y palos", "GOLF", 15000),
    ("TOALLAS", "Alquiler de toallas", "PISCINA", 1000),
    ("MOBILIARIO", "Montaje de mobiliario", "SALON_EVENTOS", 35000),
]
SOCIOS = [
    # cédula, nombre, correo, tipo de membresía
    ("110000001", "María López Jiménez", "maria.lopez@example.com", "FAMILIAR"),
    ("110000002", "Carlos Pérez Mora", "carlos.perez@example.com", "INDIVIDUAL"),
    ("110000003", "Ana Vargas Solís", "ana.vargas@example.com", "CORPORATIVA"),
    ("110000004", "Luis Mora Castro", "luis.mora@example.com", "INDIVIDUAL"),
    ("110000005", "Sofía Rojas Vega", "sofia.rojas@example.com", "HONORARIA"),
]
ADMINISTRADORES = [
    ("210000001", "Andrea Ramírez (Instalaciones)", "instalaciones@example.com", "INSTALACIONES"),
    ("210000002", "Jorge Salas (Cobros)", "cobros@example.com", "COBROS"),
    ("210000003", "Paula Méndez (Recepción)", "recepcion@example.com", "RECEPCION"),
]


def mes_anterior(periodo):
    return date(periodo.year - 1, 12, 1) if periodo.month == 1 else date(periodo.year, periodo.month - 1, 1)


class Command(BaseCommand):
    help = "Carga datos de demostración de todos los módulos (socios, reservas, cobros, invitados y notificaciones)."

    def handle(self, *args, **options):
        if User.objects.filter(email=SOCIOS[0][2]).exists():
            self.stdout.write(self.style.WARNING("Los datos de demostración ya están cargados; no se hizo ningún cambio."))
            return
        # Correos a memoria: quedan registrados como enviados sin escribir a direcciones de ejemplo.
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"), transaction.atomic():
            self.cargar()
        self.resumen()

    # ------------------------------------------------------------------
    def cargar(self):
        hoy = timezone.localdate()
        dia = lambda n: hoy + timedelta(days=n)

        # Instalaciones y servicios
        inst = {}
        for codigo, nombre, tipo, aforo, abre, cierra in INSTALACIONES:
            inst[codigo], _ = Instalacion.objects.get_or_create(codigo=codigo, defaults=dict(
                nombre=nombre, tipo_id=tipo, aforo_maximo=aforo, hora_apertura=time(abre), hora_cierre=time(cierra), activa=True))
        serv = {}
        for codigo, nombre, tipo, precio in SERVICIOS:
            serv[codigo], _ = ServicioAdicional.objects.get_or_create(codigo=codigo, defaults=dict(
                nombre=nombre, tipo_instalacion_id=tipo, precio=precio, activo=True))

        # Administradores por rol
        admins = {}
        for cedula, nombre, correo, rol in ADMINISTRADORES:
            admins[rol] = Administrator.objects.filter(email=correo).first() or Administrator.objects.create_user(
                correo, CLAVE, cedula=cedula, nombre_completo=nombre, rol=AdminRole.objects.get(pk=rol))

        # Socios con membresía, inscritos hace unos meses para tener periodos anteriores
        socios = {}
        for cedula, nombre, correo, tipo in SOCIOS:
            socio = User.objects.create_user(correo, CLAVE, cedula=cedula, nombre_completo=nombre,
                                             telefono="+50688880000", direccion="San José, Costa Rica",
                                             fecha_nacimiento=date(1988, 5, 20))
            enroll(socio, tipo)
            Membership.objects.filter(pk=socio.pk).update(fecha_inscripcion=hoy - timedelta(days=120))
            socios[cedula] = socio
        maria, carlos, ana, luis, sofia = (socios[c[0]] for c in SOCIOS)
        save_beneficiary(maria.pk, dict(cedula="130000001", nombre_completo="Roberto Castro Núñez",
                                        parentesco=Kinship.objects.get(pk="CONYUGE"), fecha_nacimiento=date(1986, 3, 2)))
        save_beneficiary(maria.pk, dict(cedula="130000002", nombre_completo="Valeria Castro López",
                                        parentesco=Kinship.objects.get(pk="HIJO"), fecha_nacimiento=date(2014, 9, 15)))

        # Estados de cuenta de los últimos tres meses
        actual = hoy.replace(day=1)
        anterior = mes_anterior(actual)
        antepasado = mes_anterior(anterior)
        for periodo in (antepasado, anterior, actual):
            generar_estados(periodo)

        # Reservas pasadas (finalizadas) para el historial y los reportes de uso
        pasadas = [  # días atrás, socio, instalación, hora inicio, horas, personas
            (2, maria, "TENIS-1", 8, 1, 2), (3, carlos, "PISCINA-1", 10, 2, 3), (5, luis, "GOLF-1", 7, 3, 4),
            (6, maria, "PISCINA-1", 14, 2, 5), (8, ana, "SALON-1", 18, 4, 60), (9, carlos, "TENIS-1", 17, 1, 2),
            (12, luis, "TENIS-1", 6, 1, 2), (15, maria, "PISCINA-1", 9, 2, 4), (18, sofia, "GOLF-1", 8, 2, 3),
            (20, carlos, "PISCINA-1", 15, 1, 2), (24, luis, "GOLF-1", 7, 3, 4), (27, maria, "TENIS-1", 18, 1, 4),
            (31, ana, "PISCINA-1", 11, 2, 6), (36, carlos, "TENIS-1", 7, 1, 2), (40, maria, "SALON-1", 19, 3, 45),
        ]
        for atras, socio, codigo, inicio, horas, personas in pasadas:
            reserva = Reserva.objects.create(socio_id=socio.pk, instalacion=inst[codigo], fecha=dia(-atras),
                                             hora_inicio=time(inicio), hora_fin=time(inicio + horas),
                                             numero_personas=personas, estado_id="FINALIZADA")
            ReservaHistorial.objects.create(reserva=reserva, accion="FINALIZADA", actor_tipo="SISTEMA",
                                            detalle="Reserva de demostración.")

        # Reservas futuras con el flujo real
        crear_reserva(dict(instalacion=inst["TENIS-1"], fecha=dia(1), hora_inicio=time(9), hora_fin=time(10),
                           numero_personas=3, servicios=[serv["RAQUETAS"], serv["BOLAS"]]), maria)
        piscina = crear_reserva(dict(instalacion=inst["PISCINA-1"], fecha=dia(2), hora_inicio=time(10), hora_fin=time(12),
                                     numero_personas=2, servicios=[serv["TOALLAS"]]), carlos)
        modificar_reserva(piscina.pk, dict(instalacion=inst["PISCINA-1"], fecha=dia(2), hora_inicio=time(10),
                                           hora_fin=time(12), numero_personas=2, servicios=[serv["TOALLAS"]]),
                          admins["INSTALACIONES"], confirmar=True)
        crear_reserva(dict(socio=luis, instalacion=inst["GOLF-1"], fecha=dia(3), hora_inicio=time(7), hora_fin=time(10),
                           numero_personas=4, servicios=[serv["CARRITO"]]), admins["INSTALACIONES"])
        crear_reserva(dict(instalacion=inst["SALON-1"], fecha=dia(10), hora_inicio=time(18), hora_fin=time(22),
                           numero_personas=80, servicios=[serv["MOBILIARIO"]]), maria)
        cancelada = crear_reserva(dict(instalacion=inst["TENIS-1"], fecha=dia(2), hora_inicio=time(17), hora_fin=time(18),
                                       numero_personas=2, servicios=[]), ana)
        cancelar_reserva(cancelada.pk, ana)

        # Bloqueos
        zona = timezone.get_default_timezone()
        en = lambda d, h: timezone.make_aware(datetime.combine(d, time(h)), zona)
        crear_bloqueo(dict(instalacion=inst["PISCINA-1"], inicio=en(dia(4), 7), fin=en(dia(4), 9),
                           motivo=CatMotivoBloqueo.objects.get(pk="MANTENIMIENTO"), descripcion="Limpieza de filtros"),
                      admins["INSTALACIONES"])
        crear_bloqueo(dict(instalacion=inst["SALON-1"], inicio=en(dia(14), 10), fin=en(dia(14), 23),
                           motivo=CatMotivoBloqueo.objects.get(pk="EVENTO_PRIVADO"), descripcion="Asamblea anual del club"),
                      admins["INSTALACIONES"])

        # Invitados (uno llega hoy, para la pantalla de Recepción)
        familiar, amigo = Relation.objects.get(pk="FAMILIAR"), Relation.objects.get(pk="AMIGO")
        register_guest(maria, dict(fecha_visita=dia(1), instalacion=inst["TENIS-1"], cedula="120000001",
                                   nombre_completo="Laura Jiménez Castro", relacion=familiar))
        register_guest(maria, dict(fecha_visita=dia(1), instalacion=inst["TENIS-1"], cedula="120000002",
                                   nombre_completo="Diego Castro Ruiz", relacion=amigo))
        register_guest(carlos, dict(fecha_visita=hoy, instalacion=inst["PISCINA-1"], cedula="120000003",
                                    nombre_completo="Andrés Solano Vargas", relacion=amigo))

        # Pagos: Carlos y María al día; Luis debe el mes anterior; Ana no ha pagado nada
        def pagar(socio, periodos, referencia):
            cargos = list(Cargo.objects.filter(socio_id=socio.pk, periodo__in=periodos).exclude(estado_id="PAGADO"))
            if cargos:
                fecha = min(min(c.fecha_limite_pago for c in cargos) - timedelta(days=2), hoy)
                registrar_pago(socio.pk, cargos, fecha, referencia, admins["COBROS"])
        for periodo in (antepasado, anterior):
            pagar(carlos, [periodo], "Transferencia SINPE")
            pagar(maria, [periodo], "Depósito bancario")
        pagar(luis, [antepasado], "Pago en caja")

        # Marca vencidos y genera recordatorios
        procesar_recordatorios()

    def resumen(self):
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
        self.stdout.write(f"Contraseña de todas las cuentas de demostración: {CLAVE}")
        self.stdout.write("Socios (entrar como socio):")
        for _, nombre, correo, tipo in SOCIOS:
            self.stdout.write(f"  {correo:<28} {nombre} · {tipo.lower()}")
        self.stdout.write("Administradores (entrar como personal administrativo):")
        for _, nombre, correo, rol in ADMINISTRADORES:
            self.stdout.write(f"  {correo:<28} {nombre}")
