from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone

from core.models import CatPermiso, CatRolAdmin


class RolPermiso(models.Model):
    """Permisos asignados a cada rol de administrador (tabla rol_permiso)."""
    pk = models.CompositePrimaryKey('rol_id', 'permiso_id')
    rol = models.ForeignKey(
        CatRolAdmin, on_delete=models.PROTECT,
        db_column='codigo_rol', related_name='permisos')
    permiso = models.ForeignKey(
        CatPermiso, on_delete=models.PROTECT,
        db_column='codigo_permiso', related_name='+')

    class Meta:
        managed = False
        db_table = 'rol_permiso'

    def __str__(self):
        return f'{self.rol_id} - {self.permiso_id}'


class Administrador(models.Model):
    cedula = models.CharField(primary_key=True, max_length=20)
    nombre_completo = models.CharField(max_length=150)
    correo = models.CharField(max_length=150)  # único sin importar mayúsculas (índice en BD)
    rol = models.ForeignKey(
        CatRolAdmin, on_delete=models.PROTECT,
        db_column='codigo_rol', related_name='administradores')
    password_hash = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        managed = False
        db_table = 'administrador'

    def __str__(self):
        return f'{self.nombre_completo} ({self.rol_id})'

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def tiene_permiso(self, codigo_permiso):
        return RolPermiso.objects.filter(
            rol_id=self.rol_id, permiso_id=codigo_permiso).exists()
