# Base de datos - Club Valle Alto

## Enfoque

La base de datos (PostgreSQL) se define en `core/sql/club_valle_alto.sql`.
El script incluye tablas, catálogos con datos iniciales, triggers, restricciones
`EXCLUDE` (reservas sin traslapes), una columna generada `tsrange` y vistas de
reportes. Django no puede generar todo eso desde modelos, así que:

| Pieza | Qué hace |
|---|---|
| `core/migrations/0001_esquema_inicial.py` | Ejecuta el script SQL completo. Es la única migración que cambia la estructura. |
| `*/models.py` (todas las apps) | Modelos con `managed = False`, mapeados 1:1 a las tablas. Sirven para el ORM. |
| `*/migrations/0001_initial.py` | Los genera `makemigrations`. Solo registran los modelos; no tocan la BD. |
| `core/sql/club_valle_alto_drop.sql` | Reversa (`python manage.py migrate core zero`). |

## Dónde está cada modelo

| App | Modelos |
|---|---|
| core | Catálogos `Cat*` |
| administradores | `Administrador`, `RolPermiso` |
| socios | `Socio` |
| usuarios | `TokenRecuperacion` |
| membresias | `Membresia`, `HistorialMembresia`, `Beneficiario` |
| instalaciones | `Instalacion`, `ServicioAdicional`, `BloqueoInstalacion`, vistas `VUsoInstalacion`, `VOcupacionFranja` |
| reservas | `Reserva`, `ReservaServicio` |
| invitados | `Invitado`, `Invitacion`, vista `VInvitadoEsperado` |
| estado_cuenta | `EstadoCuenta`, `Cargo`, vistas `VEstadoCuentaResumen`, `VSocioMoroso` |
| notificaciones | `PlantillaNotificacion`, `Notificacion` |

Las FK se llaman por la entidad y apuntan a la columna real. Ejemplo:
`reserva.socio` usa la columna `cedula_socio`, y `reserva.socio_id` es la cédula.
Los catálogos se asignan por código: `reserva.estado_id = 'CONFIRMADA'`.

## Reglas que valida la base (no hace falta repetirlas en Python)

- Reservas: sin traslapes, dentro del horario, sin exceder el aforo, fuera de
  bloqueos y con membresía activa.
- Límite de beneficiarios y de invitados por mes según el tipo de membresía.
- Historial automático de cambios de estado de la membresía.
- Cargos: `PAGADO` si y solo si hay `fecha_pago`.

Si se viola una regla, Django lanza `django.db.IntegrityError` (CHECK, EXCLUDE,
FK) o `django.db.InternalError` (RAISE EXCEPTION de los triggers). Para mostrar
el mensaje sin romper la transacción:

```python
from django.db import transaction, IntegrityError, InternalError

try:
    with transaction.atomic():
        reserva.save()
except (IntegrityError, InternalError) as e:
    mensaje = str(e).splitlines()[0]   # ej. "Se excede el aforo máximo de 4 personas"
```

## Otras notas

- Contraseñas de `Socio` y `Administrador`: use `set_password()` y
  `check_password()` (hash de Django). No son usuarios de `django.contrib.auth`.
- Cargos vencidos: `Cargo.marcar_vencidos()` ejecuta `fn_marcar_cargos_vencidos()`.
  Hay que llamarla a diario (tarea programada).
- `BloqueoInstalacion.inicio/fin` se guardan en hora local de Costa Rica
  (columna `timestamp`, ver `core/fields.py`).
- Las PK compuestas usan `models.CompositePrimaryKey` (Django 5.2 o superior).
  El admin de Django no soporta esos modelos.

## Cambiar el esquema

No edite `club_valle_alto.sql` si la base ya fue migrada. Haga esto:

1. Cree una migración vacía: `python manage.py makemigrations core --empty -n descripcion`.
2. Ponga el cambio en `migrations.RunSQL(sql=..., reverse_sql=...)`.
3. Actualice el `models.py` correspondiente.
