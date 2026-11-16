from django.db import models
from django.utils import timezone

from administradores.models import Administrador
from core.models import CatEstadoReserva
from instalaciones.models import Instalacion, ServicioAdicional
from socios.models import Socio


class Reserva(models.Model):
    """
    Reglas que aplica la base de datos (lanzan IntegrityError/InternalError):
      - Sin traslapes entre reservas PENDIENTE/CONFIRMADA de la misma
        instalación (EXCLUDE sobre la columna generada `rango`).
      - Dentro del horario de la instalación, sin exceder el aforo, fuera de
        bloqueos e instalación activa (trigger).
      - Al crearla, el socio debe tener membresía ACTIVA (trigger).

    La columna `rango` (tsrange generado) existe en la BD pero no se mapea:
    la calcula PostgreSQL a partir de fecha, hora_inicio y hora_fin.
    """
    id_reserva = models.BigAutoField(primary_key=True)
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='reservas')
    instalacion = models.ForeignKey(
        Instalacion, on_delete=models.PROTECT,
        db_column='codigo_instalacion', related_name='reservas')
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    numero_personas = models.IntegerField()  # > 0 (CHECK en BD)
    estado = models.ForeignKey(
        CatEstadoReserva, on_delete=models.PROTECT,
        db_column='codigo_estado', default='PENDIENTE', related_name='+')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    # quien confirmó / modificó / canceló
    admin = models.ForeignKey(
        Administrador, on_delete=models.PROTECT, null=True, blank=True,
        db_column='cedula_admin', related_name='+')

    class Meta:
        managed = False
        db_table = 'reserva'

    def __str__(self):
        return (f'#{self.id_reserva} {self.instalacion_id} {self.fecha} '
                f'{self.hora_inicio:%H:%M}-{self.hora_fin:%H:%M}')


class ReservaServicio(models.Model):
    """Servicios adicionales de una reserva (precio congelado al reservar)."""
    pk = models.CompositePrimaryKey('reserva_id', 'servicio_id')
    # ON DELETE CASCADE lo hace la base de datos
    reserva = models.ForeignKey(
        Reserva, on_delete=models.DO_NOTHING,
        db_column='id_reserva', related_name='servicios')
    servicio = models.ForeignKey(
        ServicioAdicional, on_delete=models.PROTECT,
        db_column='codigo_servicio', related_name='+')
    cantidad = models.IntegerField(default=1)  # > 0 (CHECK en BD)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'reserva_servicio'

    def __str__(self):
        return f'{self.reserva_id} - {self.servicio_id} x{self.cantidad}'

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class ReservaHistorial(models.Model):
    """
    Registro de cambios de cada reserva. Extensión propia (no está en el SQL
    original): la crea la migración reservas/0002 y la administra Django.
    """
    class Accion(models.TextChoices):
        CREADA = 'CREADA', 'Creada'
        MODIFICADA = 'MODIFICADA', 'Modificada'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        FINALIZADA = 'FINALIZADA', 'Finalizada'

    class Actor(models.TextChoices):
        SOCIO = 'SOCIO', 'Socio'
        ADMIN = 'ADMIN', 'Administración'
        SISTEMA = 'SISTEMA', 'Sistema'

    id_historial = models.BigAutoField(primary_key=True)
    reserva = models.ForeignKey(
        Reserva, on_delete=models.CASCADE,
        db_column='id_reserva', related_name='historial')
    fecha = models.DateTimeField(default=timezone.now)
    accion = models.CharField(max_length=20, choices=Accion.choices)
    actor_tipo = models.CharField(max_length=10, choices=Actor.choices)
    actor_cedula = models.CharField(max_length=20, blank=True)
    actor_nombre = models.CharField(max_length=150, blank=True)
    detalle = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = 'reserva_historial'
        ordering = ['-fecha', '-id_historial']

    def __str__(self):
        return f'#{self.reserva_id} {self.accion} ({self.fecha:%Y-%m-%d %H:%M})'
