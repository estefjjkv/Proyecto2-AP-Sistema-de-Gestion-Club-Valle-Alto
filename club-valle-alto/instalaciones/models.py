from django.db import models
from django.utils import timezone

from administradores.models import Administrador
from core.fields import FechaHoraLocalField
from core.models import CatMotivoBloqueo, CatTipoInstalacion


class Instalacion(models.Model):
    codigo = models.CharField(primary_key=True, max_length=30)  # ej. 'TENIS-1', 'PISCINA-A'
    nombre = models.CharField(max_length=100)
    tipo = models.ForeignKey(
        CatTipoInstalacion, on_delete=models.PROTECT,
        db_column='codigo_tipo', related_name='instalaciones')
    aforo_maximo = models.IntegerField()  # > 0 (CHECK en BD)
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()      # > hora_apertura (CHECK en BD)
    activa = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'instalacion'

    def __str__(self):
        return self.nombre


class ServicioAdicional(models.Model):
    """Alquiler de equipo, montaje de mobiliario, etc."""
    codigo = models.CharField(primary_key=True, max_length=30)
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    tipo_instalacion = models.ForeignKey(
        CatTipoInstalacion, on_delete=models.PROTECT,
        db_column='codigo_tipo_instalacion', related_name='servicios')
    precio = models.DecimalField(max_digits=12, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'servicio_adicional'

    def __str__(self):
        return self.nombre


class BloqueoInstalacion(models.Model):
    """
    Bloqueo por mantenimiento o evento privado. La base rechaza bloqueos
    traslapados en la misma instalación (EXCLUDE) y reservas dentro de un
    bloqueo (trigger de reserva). inicio/fin van en hora local del club.
    """
    id_bloqueo = models.BigAutoField(primary_key=True)
    instalacion = models.ForeignKey(
        Instalacion, on_delete=models.PROTECT,
        db_column='codigo_instalacion', related_name='bloqueos')
    inicio = FechaHoraLocalField()
    fin = FechaHoraLocalField()
    motivo = models.ForeignKey(
        CatMotivoBloqueo, on_delete=models.PROTECT,
        db_column='codigo_motivo', related_name='+')
    descripcion = models.CharField(max_length=300, null=True, blank=True)
    admin = models.ForeignKey(
        Administrador, on_delete=models.PROTECT,
        db_column='cedula_admin', related_name='+')
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'bloqueo_instalacion'

    def __str__(self):
        return f'{self.instalacion_id}: {self.inicio} - {self.fin} ({self.motivo_id})'


# ---------------------------------------------------------------------
# Vistas de reportes (solo lectura)
# ---------------------------------------------------------------------

class VUsoInstalacion(models.Model):
    """Vista v_uso_instalaciones: reservas confirmadas/finalizadas por mes."""
    pk = models.CompositePrimaryKey('codigo_instalacion', 'periodo')
    codigo_instalacion = models.CharField(max_length=30)
    periodo = models.DateField()
    total_reservas = models.BigIntegerField()
    horas_reservadas = models.DecimalField(max_digits=14, decimal_places=2)
    total_personas = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'v_uso_instalaciones'


class VOcupacionFranja(models.Model):
    """Vista v_ocupacion_franja: ocupación de reservas vigentes."""
    pk = models.CompositePrimaryKey('codigo_instalacion', 'fecha', 'hora_inicio')
    codigo_instalacion = models.CharField(max_length=30)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    numero_personas = models.IntegerField()
    aforo_maximo = models.IntegerField()
    porcentaje_ocupacion = models.DecimalField(max_digits=6, decimal_places=1)

    class Meta:
        managed = False
        db_table = 'v_ocupacion_franja'
