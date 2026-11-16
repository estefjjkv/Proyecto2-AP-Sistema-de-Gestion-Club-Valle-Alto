from django.db import models
from django.utils import timezone
from django.core import signing


class Guest(models.Model):
    cedula = models.CharField(max_length=20, primary_key=True)
    nombre_completo = models.CharField(max_length=150)
    class Meta:
        managed = False
        db_table = "invitado"
    def __str__(self): return self.nombre_completo


class Relation(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        managed = False
        db_table = "cat_relacion_invitado"
    def __str__(self): return self.descripcion


class GuestVisit(models.Model):
    pk = models.CompositePrimaryKey("socio_id", "invitado_id", "fecha_visita", "instalacion_id")
    socio = models.ForeignKey("accounts.User", db_column="cedula_socio", on_delete=models.PROTECT)
    invitado = models.ForeignKey(Guest, db_column="cedula_invitado", on_delete=models.PROTECT)
    fecha_visita = models.DateField()
    instalacion = models.ForeignKey("instalaciones.Instalacion", db_column="codigo_instalacion", on_delete=models.PROTECT)
    relacion = models.ForeignKey(Relation, db_column="codigo_relacion", on_delete=models.PROTECT)
    id_reserva = models.BigIntegerField(null=True, blank=True)
    creado = models.DateTimeField(default=timezone.now, db_column="fecha_registro")
    @property
    def nombre_completo(self): return self.invitado.nombre_completo
    @property
    def cedula(self): return self.invitado_id
    @property
    def membresia(self): return self.socio.membresia
    @property
    def referencia(self):
        return signing.dumps([self.socio_id, self.invitado_id, self.fecha_visita.isoformat(), self.instalacion_id], salt="guest-entry")
    @property
    def ingreso(self):
        entry = GuestEntry.objects.filter(socio=self.socio_id, invitado=self.invitado_id, fecha_visita=self.fecha_visita, instalacion=self.instalacion_id).first()
        return entry.ingreso if entry else None
    def get_relacion_display(self): return str(self.relacion)
    class Meta:
        managed = False
        db_table = "invitacion"
        ordering = ["-fecha_visita", "invitado_id"]


class GuestEntry(models.Model):
    # El SQL original no guarda ingreso. Extensión separada sin alterar invitacion.
    pk = models.CompositePrimaryKey("socio", "invitado", "fecha_visita", "instalacion")
    socio = models.CharField(max_length=20)
    invitado = models.CharField(max_length=20)
    fecha_visita = models.DateField()
    instalacion = models.CharField(max_length=30)
    ingreso = models.DateTimeField(default=timezone.now)
    class Meta:
        db_table = "backend1_ingreso_invitado"
