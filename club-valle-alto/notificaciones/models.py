from django.db import models
from django.utils import timezone

from administradores.models import Administrador
from core.models import CatEstadoEnvio, CatTipoNotificacion
from reservas.models import Reserva
from socios.models import Socio


class PlantillaNotificacion(models.Model):
    """Una plantilla por tipo de notificación. El cuerpo admite {{nombre}}, {{detalle}}, etc."""
    tipo = models.OneToOneField(
        CatTipoNotificacion, on_delete=models.PROTECT, primary_key=True,
        db_column='codigo_tipo', related_name='plantilla')
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    admin = models.ForeignKey(
        Administrador, on_delete=models.PROTECT, null=True, blank=True,
        db_column='cedula_admin', related_name='+')
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'plantilla_notificacion'

    def __str__(self):
        return self.asunto

    def renderizar(self, **valores):
        """Reemplaza {{clave}} por su valor en asunto y cuerpo. Devuelve (asunto, cuerpo)."""
        asunto, cuerpo = self.asunto, self.cuerpo
        for clave, valor in valores.items():
            asunto = asunto.replace('{{%s}}' % clave, str(valor))
            cuerpo = cuerpo.replace('{{%s}}' % clave, str(valor))
        return asunto, cuerpo


class Notificacion(models.Model):
    """Historial de notificaciones enviadas a los socios."""
    id_notificacion = models.BigAutoField(primary_key=True)
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='notificaciones')
    tipo = models.ForeignKey(
        CatTipoNotificacion, on_delete=models.PROTECT,
        db_column='codigo_tipo', related_name='+')
    correo_destino = models.CharField(max_length=150)
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    estado = models.ForeignKey(
        CatEstadoEnvio, on_delete=models.PROTECT,
        db_column='codigo_estado', default='PENDIENTE', related_name='+')
    # ON DELETE SET NULL lo hace la base de datos
    reserva = models.ForeignKey(
        Reserva, on_delete=models.DO_NOTHING, null=True, blank=True,
        db_column='id_reserva', related_name='notificaciones')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'notificacion'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f'{self.tipo_id} -> {self.correo_destino} ({self.estado_id})'
