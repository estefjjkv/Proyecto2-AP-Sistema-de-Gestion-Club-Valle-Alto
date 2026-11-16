"""
Catálogos del sistema (tablas cat_*).

Todos los modelos del proyecto usan managed = False: la estructura la crea
core/migrations/0001_esquema_inicial.py (script SQL). Django solo los usa
para consultar, insertar, actualizar y borrar datos.
"""
from django.db import models


class Catalogo(models.Model):
    """Base de los catálogos: PK = código textual corto."""
    codigo = models.CharField(primary_key=True, max_length=20)
    descripcion = models.CharField(max_length=100)

    class Meta:
        abstract = True
        managed = False

    def __str__(self):
        return self.descripcion


class CatEstadoCuentaSocio(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_estado_cuenta_socio'


class CatTipoMembresia(Catalogo):
    cuota_base = models.DecimalField(max_digits=12, decimal_places=2)
    limite_beneficiarios = models.PositiveSmallIntegerField(default=0)
    limite_invitados_mes = models.PositiveSmallIntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'cat_tipo_membresia'


class CatEstadoMembresia(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_estado_membresia'


class CatParentesco(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_parentesco'


class CatRelacionInvitado(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_relacion_invitado'


class CatTipoInstalacion(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_tipo_instalacion'


class CatEstadoReserva(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_estado_reserva'


class CatMotivoBloqueo(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_motivo_bloqueo'


class CatRolAdmin(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_rol_admin'


class CatPermiso(Catalogo):
    codigo = models.CharField(primary_key=True, max_length=40)
    descripcion = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'cat_permiso'


class CatTipoCargo(Catalogo):
    codigo = models.CharField(primary_key=True, max_length=30)

    class Meta:
        managed = False
        db_table = 'cat_tipo_cargo'


class CatEstadoCargo(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_estado_cargo'


class CatTipoNotificacion(Catalogo):
    codigo = models.CharField(primary_key=True, max_length=40)
    descripcion = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = 'cat_tipo_notificacion'


class CatEstadoEnvio(Catalogo):
    class Meta:
        managed = False
        db_table = 'cat_estado_envio'
