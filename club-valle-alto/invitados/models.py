from django.db import models
from django.utils import timezone

from core.models import CatRelacionInvitado
from instalaciones.models import Instalacion
from reservas.models import Reserva
from socios.models import Socio


class Invitado(models.Model):
    cedula = models.CharField(primary_key=True, max_length=20)
    nombre_completo = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'invitado'

    def __str__(self):
        return f'{self.nombre_completo} ({self.cedula})'


class Invitacion(models.Model):
    """
    Invitación: socio + invitado + fecha + instalación (clave natural).
    La base rechaza (trigger) superar el límite mensual de invitados del
    tipo de membresía y exige membresía ACTIVA.
    """
    pk = models.CompositePrimaryKey(
        'socio_id', 'invitado_id', 'fecha_visita', 'instalacion_id')
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='invitaciones')
    invitado = models.ForeignKey(
        Invitado, on_delete=models.PROTECT,
        db_column='cedula_invitado', related_name='invitaciones')
    fecha_visita = models.DateField()
    instalacion = models.ForeignKey(
        Instalacion, on_delete=models.PROTECT,
        db_column='codigo_instalacion', related_name='invitaciones')
    relacion = models.ForeignKey(
        CatRelacionInvitado, on_delete=models.PROTECT,
        db_column='codigo_relacion', related_name='+')
    # opcional; ON DELETE SET NULL lo hace la base de datos
    reserva = models.ForeignKey(
        Reserva, on_delete=models.DO_NOTHING, null=True, blank=True,
        db_column='id_reserva', related_name='invitaciones')
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'invitacion'

    def __str__(self):
        return f'{self.invitado_id} invitado por {self.socio_id} el {self.fecha_visita}'


class VInvitadoEsperado(models.Model):
    """Vista v_invitados_esperados (listado de recepción, solo lectura)."""
    pk = models.CompositePrimaryKey(
        'cedula_socio', 'cedula_invitado', 'fecha_visita', 'codigo_instalacion')
    fecha_visita = models.DateField()
    codigo_instalacion = models.CharField(max_length=30)
    cedula_invitado = models.CharField(max_length=20)
    nombre_invitado = models.CharField(max_length=150)
    codigo_relacion = models.CharField(max_length=20)
    cedula_socio = models.CharField(max_length=20)
    nombre_socio = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'v_invitados_esperados'
