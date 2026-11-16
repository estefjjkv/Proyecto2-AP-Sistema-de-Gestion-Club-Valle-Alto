from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from core.models import CatEstadoCuentaSocio


class Socio(models.Model):
    cedula = models.CharField(primary_key=True, max_length=20)
    nombre_completo = models.CharField(max_length=150)
    correo = models.CharField(max_length=150)  # único sin importar mayúsculas (índice en BD)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=300)
    fecha_nacimiento = models.DateField()
    password_hash = models.CharField(max_length=255)
    estado = models.ForeignKey(
        CatEstadoCuentaSocio, on_delete=models.PROTECT,
        db_column='codigo_estado', default='ACTIVA', related_name='+')
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)  # bloqueo por intentos fallidos
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'socio'

    def __str__(self):
        return f'{self.nombre_completo} ({self.cedula})'

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)
