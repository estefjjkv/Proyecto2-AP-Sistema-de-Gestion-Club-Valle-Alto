from django.db import connection, models
from django.utils import timezone

from administradores.models import Administrador
from core.models import CatEstadoCargo, CatTipoCargo
from reservas.models import Reserva
from socios.models import Socio


class EstadoCuenta(models.Model):
    """Un estado de cuenta por socio y periodo (periodo = día 1 del mes)."""
    pk = models.CompositePrimaryKey('socio_id', 'periodo')
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='estados_cuenta')
    periodo = models.DateField()
    fecha_generacion = models.DateTimeField(default=timezone.now)
    fecha_limite_pago = models.DateField()

    class Meta:
        managed = False
        db_table = 'estado_cuenta'
        ordering = ['-periodo']

    def __str__(self):
        return f'{self.socio_id} - {self.periodo:%Y-%m}'

    @property
    def cargos(self):
        # Django no permite ForeignKey hacia una PK compuesta: se filtra a mano.
        return Cargo.objects.filter(socio_id=self.socio_id, periodo=self.periodo)


class Cargo(models.Model):
    """
    Rubro de un estado de cuenta. En la BD existe la FK compuesta
    (cedula_socio, periodo) -> estado_cuenta: el estado de cuenta debe
    existir antes de crear sus cargos.

    CHECK en BD: codigo_estado = 'PAGADO' si y solo si fecha_pago no es NULL.
    """
    id_cargo = models.BigAutoField(primary_key=True)
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='cargos')
    periodo = models.DateField()
    tipo = models.ForeignKey(
        CatTipoCargo, on_delete=models.PROTECT,
        db_column='codigo_tipo', related_name='+')
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_limite_pago = models.DateField()
    estado = models.ForeignKey(
        CatEstadoCargo, on_delete=models.PROTECT,
        db_column='codigo_estado', default='PENDIENTE', related_name='+')
    fecha_pago = models.DateTimeField(null=True, blank=True)
    # quien registró el pago
    admin_pago = models.ForeignKey(
        Administrador, on_delete=models.PROTECT, null=True, blank=True,
        db_column='cedula_admin_pago', related_name='+')
    # ON DELETE SET NULL lo hace la base de datos
    reserva = models.ForeignKey(
        Reserva, on_delete=models.DO_NOTHING, null=True, blank=True,
        db_column='id_reserva', related_name='cargos')

    class Meta:
        managed = False
        db_table = 'cargo'

    def __str__(self):
        return f'#{self.id_cargo} {self.descripcion} ({self.estado_id})'

    @property
    def estado_cuenta(self):
        return EstadoCuenta.objects.get(socio_id=self.socio_id, periodo=self.periodo)

    @staticmethod
    def marcar_vencidos():
        """Ejecuta fn_marcar_cargos_vencidos() (correr a diario). Devuelve cuántos cambió."""
        with connection.cursor() as cursor:
            cursor.execute('SELECT fn_marcar_cargos_vencidos()')
            return cursor.fetchone()[0]


# ---------------------------------------------------------------------
# Vistas de reportes (solo lectura)
# ---------------------------------------------------------------------

class VEstadoCuentaResumen(models.Model):
    """Vista v_estado_cuenta_resumen: totales por socio y periodo."""
    pk = models.CompositePrimaryKey('cedula_socio', 'periodo')
    cedula_socio = models.CharField(max_length=20)
    periodo = models.DateField()
    fecha_limite_pago = models.DateField()
    total = models.DecimalField(max_digits=14, decimal_places=2)
    pagado = models.DecimalField(max_digits=14, decimal_places=2)
    pendiente = models.DecimalField(max_digits=14, decimal_places=2)
    vencido = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'v_estado_cuenta_resumen'


class VSocioMoroso(models.Model):
    """Vista v_socios_morosos: socios con cargos sin pagar después de la fecha límite."""
    cedula = models.CharField(primary_key=True, max_length=20)
    nombre_completo = models.CharField(max_length=150)
    correo = models.CharField(max_length=150)
    cargos_atrasados = models.BigIntegerField()
    monto_adeudado = models.DecimalField(max_digits=14, decimal_places=2)
    dias_atraso_max = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'v_socios_morosos'


# ---------------------------------------------------------------------
# Pagos manuales (extensión propia: migración estado_cuenta/0002)
# ---------------------------------------------------------------------

class Pago(models.Model):
    """
    Recepción de un pago registrada por administración. Cada pago salda uno
    o varios cargos completos (ver PagoCargo). No se procesan pagos en línea.
    """
    id_pago = models.BigAutoField(primary_key=True)
    socio = models.ForeignKey(
        Socio, on_delete=models.PROTECT,
        db_column='cedula_socio', related_name='pagos')
    fecha_pago = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    referencia = models.CharField(max_length=200, blank=True)
    admin = models.ForeignKey(
        Administrador, on_delete=models.PROTECT,
        db_column='cedula_admin', related_name='+')
    fecha_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'pago'
        ordering = ['-fecha_registro', '-id_pago']

    def __str__(self):
        return f'Pago #{self.id_pago} de {self.socio_id} ({self.monto})'


class PagoCargo(models.Model):
    """Cargo saldado por un pago. Un cargo solo puede pagarse una vez."""
    pago = models.ForeignKey(
        Pago, on_delete=models.PROTECT,
        db_column='id_pago', related_name='detalles')
    cargo = models.OneToOneField(
        Cargo, on_delete=models.PROTECT,
        db_column='id_cargo', related_name='pago_detalle')
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'pago_cargo'

    def __str__(self):
        return f'Pago #{self.pago_id} -> cargo #{self.cargo_id}'
