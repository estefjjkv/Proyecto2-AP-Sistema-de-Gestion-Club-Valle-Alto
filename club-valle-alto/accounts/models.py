from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone
from .validators import normalize_id, normalize_phone, past_birth


class ClubManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, *args, **kwargs):
        raise ValueError("Use python manage.py crear_administrador; los administradores viven en la tabla administrador.")


class Identity(AbstractBaseUser):
    # AbstractBaseUser aporta hashing y autenticación; no inventamos last_login.
    last_login = None
    cedula = models.CharField("cédula", max_length=20, primary_key=True)
    nombre_completo = models.CharField("nombre completo", max_length=150)
    email = models.EmailField("correo electrónico", max_length=150, db_column="correo", unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    failed_attempts = models.PositiveSmallIntegerField(default=0, db_column="intentos_fallidos")
    locked_until = models.DateTimeField(null=True, blank=True, db_column="bloqueado_hasta")
    objects = ClubManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["cedula", "nombre_completo"]

    class Meta:
        abstract = True

    @property
    def is_staff(self): return False
    @property
    def is_superuser(self): return False
    def get_full_name(self): return self.nombre_completo
    def get_short_name(self): return self.nombre_completo
    def has_perm(self, perm, obj=None):
        from django.contrib.auth import get_backends
        return any(backend.has_perm(self, perm, obj) for backend in get_backends())
    def has_module_perms(self, app_label): return False
    def __str__(self): return self.nombre_completo
    def clean(self):
        super().clean()
        self.email = self.email.strip().lower()
        # No reescribir PK existentes: otros módulos referencian la cédula literal.
        if self._state.adding:
            self.cedula = normalize_id(self.cedula)
    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class User(Identity):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVA", "Activa"
        SUSPENDED = "SUSPENDIDA", "Suspendida"
        DISABLED = "DESACTIVADA", "Desactivada"
    telefono = models.CharField("teléfono", max_length=20)
    direccion = models.CharField("dirección", max_length=300)
    fecha_nacimiento = models.DateField("fecha de nacimiento", validators=[past_birth])
    estado = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_column="codigo_estado")
    date_joined = models.DateTimeField(default=timezone.now, db_column="fecha_registro")
    @property
    def rol(self): return "socio"
    @property
    def is_active(self): return self.estado == "ACTIVA"
    class Meta:
        managed = False
        db_table = "socio"


class AdminRole(models.Model):
    codigo = models.CharField(max_length=20, primary_key=True)
    descripcion = models.CharField(max_length=100)
    class Meta:
        managed = False
        db_table = "cat_rol_admin"
    def __str__(self): return self.descripcion


class RolePermission(models.Model):
    pk = models.CompositePrimaryKey("codigo_rol", "codigo_permiso")
    codigo_rol = models.CharField(max_length=20)
    codigo_permiso = models.CharField(max_length=40)
    class Meta:
        managed = False
        db_table = "rol_permiso"


class Administrator(Identity):
    rol = models.ForeignKey(AdminRole, db_column="codigo_rol", on_delete=models.PROTECT)
    activo = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now, db_column="fecha_creacion")
    @property
    def is_active(self): return self.activo
    def get_rol_display(self): return str(self.rol)
    def get_estado_display(self): return "Activa" if self.activo else "Desactivada"
    class Meta:
        managed = False
        db_table = "administrador"


class RecoveryToken(models.Model):
    token_hash = models.CharField(max_length=64, primary_key=True)
    socio = models.ForeignKey(User, db_column="cedula_socio", on_delete=models.CASCADE)
    fecha_expira = models.DateTimeField()
    usado = models.BooleanField(default=False)
    fecha_creado = models.DateTimeField(default=timezone.now)
    class Meta:
        managed = False
        db_table = "token_recuperacion"


class AccountEvent(models.Model):
    # Tabla auxiliar de auditoría. No duplica identidades del SQL original.
    target_kind = models.CharField(max_length=15)
    target_id = models.CharField(max_length=20)
    actor_id = models.CharField(max_length=20, blank=True)
    actor_kind = models.CharField(max_length=15, blank=True)
    action = models.CharField(max_length=80)
    detail = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "backend1_evento_cuenta"
        ordering = ["-created_at", "-pk"]
