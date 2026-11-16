from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from accounts.validators import past_birth


class MembershipType(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=100, db_column="descripcion")
    cuota = models.DecimalField(max_digits=12, decimal_places=2, db_column="cuota_base", validators=[MinValueValidator(0)])
    limite_beneficiarios = models.PositiveSmallIntegerField(default=0)
    limite_invitados = models.PositiveSmallIntegerField(default=0, db_column="limite_invitados_mes")
    @property
    def categoria(self): return self.codigo.lower()
    def clean(self):
        if self.codigo != "FAMILIAR" and self.limite_beneficiarios:
            raise ValidationError("Solo FAMILIAR admite beneficiarios en este proyecto.")
    def __str__(self): return self.nombre
    class Meta:
        managed = False
        db_table = "cat_tipo_membresia"


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVA", "Activa"
        SUSPENDED = "SUSPENDIDA", "Suspendida"
        EXPIRED = "VENCIDA", "Vencida"
        CANCELLED = "BAJA", "De baja"
    socio = models.OneToOneField("accounts.User", primary_key=True, db_column="cedula_socio", on_delete=models.PROTECT, related_name="membresia")
    tipo = models.ForeignKey(MembershipType, db_column="codigo_tipo", on_delete=models.PROTECT)
    fecha_inscripcion = models.DateField(default=timezone.localdate)
    fecha_renovacion = models.DateField()
    cuota = models.DecimalField(max_digits=12, decimal_places=2, db_column="monto_cuota", validators=[MinValueValidator(0)])
    estado = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_column="codigo_estado")
    @property
    def estado_efectivo(self):
        if self.estado == "ACTIVA" and self.fecha_renovacion < timezone.localdate(): return "VENCIDA"
        return self.estado
    @property
    def vigente(self):
        return self.estado_efectivo == "ACTIVA" and self.fecha_inscripcion <= timezone.localdate()
    def clean(self):
        if self.fecha_renovacion and self.fecha_inscripcion and self.fecha_renovacion <= self.fecha_inscripcion:
            raise ValidationError("La renovación debe ser posterior a la inscripción (regla del SQL).")
    def __str__(self): return f"{self.socio} · {self.tipo}"
    class Meta:
        managed = False
        db_table = "membresia"


class MembershipHistory(models.Model):
    pk = models.CompositePrimaryKey("membresia_id", "fecha")
    membresia = models.ForeignKey(Membership, db_column="cedula_socio", on_delete=models.PROTECT, related_name="historial")
    fecha = models.DateTimeField(db_column="fecha_cambio", default=timezone.now)
    anterior = models.CharField(max_length=20, null=True, blank=True, db_column="estado_anterior")
    nuevo = models.CharField(max_length=20, db_column="estado_nuevo")
    actor = models.ForeignKey("accounts.Administrator", null=True, blank=True, db_column="cedula_admin", on_delete=models.PROTECT)
    motivo = models.CharField(max_length=300, blank=True, null=True)
    class Meta:
        managed = False
        db_table = "historial_membresia"
        ordering = ["-fecha"]


class Kinship(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        managed = False
        db_table = "cat_parentesco"
    def __str__(self): return self.descripcion


class Beneficiary(models.Model):
    pk = models.CompositePrimaryKey("membresia_id", "cedula")
    membresia = models.ForeignKey(Membership, db_column="cedula_titular", on_delete=models.CASCADE, related_name="beneficiarios")
    cedula = models.CharField("cédula", max_length=20, db_column="cedula_beneficiario")
    nombre_completo = models.CharField(max_length=150)
    parentesco = models.ForeignKey(Kinship, db_column="codigo_parentesco", on_delete=models.PROTECT)
    fecha_nacimiento = models.DateField(validators=[past_birth])
    def get_parentesco_display(self): return str(self.parentesco)
    def __str__(self): return self.nombre_completo
    class Meta:
        managed = False
        db_table = "beneficiario"
