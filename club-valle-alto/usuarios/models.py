from django.db import models
from django.utils import timezone

from socios.models import Socio


class TokenRecuperacion(models.Model):
    """Enlace de recuperación de contraseña. Se guarda el hash del token, no el token."""
    token_hash = models.CharField(primary_key=True, max_length=64)
    # ON DELETE CASCADE lo hace la base de datos
    socio = models.ForeignKey(
        Socio, on_delete=models.DO_NOTHING,
        db_column='cedula_socio', related_name='tokens_recuperacion')
    fecha_expira = models.DateTimeField()
    usado = models.BooleanField(default=False)
    fecha_creado = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'token_recuperacion'

    def __str__(self):
        return f'Token de {self.socio_id} (expira {self.fecha_expira:%Y-%m-%d %H:%M})'
