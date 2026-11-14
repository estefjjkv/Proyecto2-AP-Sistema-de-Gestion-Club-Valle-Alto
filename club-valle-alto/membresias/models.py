from django.db import models
from django.utils import timezone

from administradores.models import Administrador
from core.models import CatEstadoMembresia, CatParentesco, CatTipoMembresia
from socios.models import Socio


class Membresia(models.Model):
    """
    Una membresía por socio (PK = cédula del socio).

    Reglas que aplica la base de datos:
      - Cada cambio de codigo_estado se registra solo en historial_membresia
        (trigger). Para guardar quién lo hizo y el motivo, actualice después
        la fila del historial (cedula_admin y motivo).
      - fecha_renovacion > fecha_inscripcion.
    """
    socio = models.OneToOneField(
        Socio, on_delete=models.PROTECT, primary_key=True,
        db_column='cedula_socio', related_name='membresia')
    tipo = models.ForeignKey(
        CatTipoMembresia, on_delete=models.PROTECT,
        db_column='codigo_tipo', related_name='+')
    fecha_inscripcion = models.DateField(default=timezone.localdate)
    fecha_renovacion = models.DateField()
    monto_cuota = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.ForeignKey(
        CatEstadoMembresia, on_delete=models.PROTECT,
        db_column='codigo_estado', default='ACTIVA', related_name='+')

    class Meta:
        managed = False
        db_table = 'membresia'

    def __str__(self):
        return f'{self.socio_id} - {self.tipo_id} ({self.estado_id})'


class HistorialMembresia(models.Model):
    """Lo llena el trigger trg_historial_membresia; normalmente solo se consulta."""
    pk = models.CompositePrimaryKey('membresia_id', 'fecha_cambio')
    membresia = models.ForeignKey(
        Membresia, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='historial')
    fecha_cambio = models.DateTimeField(default=timezone.now)
    estado_anterior = models.ForeignKey(
        CatEstadoMembresia, on_delete=models.PROTECT, null=True, blank=True,
        db_column='estado_anterior', related_name='+')
    estado_nuevo = models.ForeignKey(
        CatEstadoMembresia, on_delete=models.PROTECT,
        db_column='estado_nuevo', related_name='+')
    admin = models.ForeignKey(
        Administrador, on_delete=models.PROTECT, null=True, blank=True,
        db_column='cedula_admin', related_name='+')
    motivo = models.CharField(max_length=300, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'historial_membresia'
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f'{self.membresia_id}: {self.estado_anterior_id} -> {self.estado_nuevo_id}'


class Beneficiario(models.Model):
    """
    Beneficiario de una membresía. La base rechaza (trigger) superar el
    límite de beneficiarios del tipo de membresía.
    """
    pk = models.CompositePrimaryKey('titular_id', 'cedula_beneficiario')
    # ON DELETE CASCADE lo hace la base de datos
    titular = models.ForeignKey(
        Membresia, on_delete=models.DO_NOTHING,
        db_column='cedula_titular', related_name='beneficiarios')
    cedula_beneficiario = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=150)
    parentesco = models.ForeignKey(
        CatParentesco, on_delete=models.PROTECT,
        db_column='codigo_parentesco', related_name='+')
    fecha_nacimiento = models.DateField()

    class Meta:
        managed = False
        db_table = 'beneficiario'

    def __str__(self):
        return f'{self.nombre_completo} ({self.parentesco_id} de {self.titular_id})'
