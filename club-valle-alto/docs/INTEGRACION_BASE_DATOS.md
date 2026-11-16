# Integración con club_valle_alto.sql

## Fuente y propiedad del esquema

El SQL activo es `core/sql/club_valle_alto.sql`, idéntico al del repositorio DataBase recibido. core/0001 lo ejecuta una sola vez. Se preservan todas las migraciones iniciales del equipo; las migraciones de soporte del Backend 1 dependen de la existencia del esquema.

Las entidades usan managed=False y mapeos explícitos. Se conservan los modelos originales del equipo y los modelos de servicio/autenticación del backend: ambos leen las mismas tablas, sin duplicar datos. No se trata de migrar automáticamente registros desde una db.sqlite3 anterior. Consulta MIGRACIONES_REPOSITORIO.md para bases PostgreSQL ya instaladas.

| Modelo Python | Tabla original | Identificador |
|---|---|---|
| accounts.User | socio | cedula |
| accounts.Administrator | administrador | cedula |
| accounts.AdminRole / RolePermission | cat_rol_admin / rol_permiso | codigo / (codigo_rol, codigo_permiso) |
| accounts.RecoveryToken | token_recuperacion | token_hash |
| memberships.MembershipType | cat_tipo_membresia | codigo |
| memberships.Membership | membresia | cedula_socio |
| memberships.Beneficiary | beneficiario | (cedula_titular, cedula_beneficiario) |
| memberships.MembershipHistory | historial_membresia | (cedula_socio, fecha_cambio) |
| guests.Guest | invitado | cedula |
| guests.GuestVisit | invitacion | (cedula_socio, cedula_invitado, fecha_visita, codigo_instalacion) |
| instalaciones.Instalacion | instalacion | codigo |

Los catálogos de parentesco y relación se consultan desde sus tablas. Se respetan estados y códigos en MAYÚSCULAS. `email` mapea a `correo`; `password` a `password_hash`; la cuota de una membresía a `monto_cuota`.

## Complementos que aplica migrate

1. Tablas propias de Django: sesiones, historial de migraciones, content types y tablas estándar de auth. Las identidades del club siguen únicamente en socio y administrador. Los permisos efectivos del portal se consultan desde `rol_permiso`, no desde auth_group.
2. `backend1_evento_cuenta`: auditoría de alta, estados y contraseñas. Registra tipo de identidad además de cédula para evitar confundir a un socio con un administrador.
3. `backend1_ingreso_invitado`: hora de ingreso, con clave compuesta y FK a la invitación original; al eliminar la invitación se elimina este registro auxiliar.
4. Rol RECEPCION con CONSULTAR_INVITADOS; se inserta solo si no existe. No se reemplazan los roles y permisos originales.
5. Se reemplaza únicamente `fn_historial_membresia`, manteniendo el mismo trigger, tabla y columnas. El repositorio ya usa clock_timestamp(); la función integrada añade una fecha estrictamente creciente y lee administrador/motivo de parámetros locales de la transacción.

El complemento de historial y recepción se puede revisar en `database/002_soporte_backend1.sql`; lo ejecuta `memberships/migrations/0002_historial_y_recepcion.py`. **No es necesario ejecutarlo a mano además de migrate.** Revertir esa migración restaura la función original, pero conserva el rol RECEPCION para no romper cuentas que ya lo usen.

No se modifican funciones ni tablas de reservas, cargos, estados de cuenta, notificaciones o bloqueos. Se requiere acordar el complemento de historial con quien mantenga la base para conservarlo si vuelve a instalar el esquema original.

## Identidades, contraseñas y sesiones

Socio y administrador pueden tener la misma cédula e incluso el mismo correo porque el SQL los separa. La pantalla de login pide el tipo de cuenta. Dos backends de autenticación conservan el tipo en la sesión; los permisos no se deducen solo del valor de la cédula.

Los usuarios nuevos guardan hashes compatibles con los algoritmos de Django (por defecto PBKDF2); nunca contraseñas en texto claro. Si se cargaron cuentas mediante SQL con otro formato de hash, hay que establecer contraseñas compatibles mediante el flujo de recuperación o administración. No se convierten hashes antiguos automáticamente. No se usa Supabase Auth: se usa el esquema socio/administrador entregado por el equipo.

La cédula de una cuenta existente no se edita desde el perfil, pues la referencian varios módulos. Para nuevas identificaciones se eliminan guiones/espacios y se usan mayúsculas. Las claves existentes no se reescriben al abrirlas.

## Reglas y concurrencia

- Una membresía por socio; nunca se transfiere a otro titular. Las bajas conservan la fila.
- Solo FAMILIAR admite beneficiarios en este proyecto. Los límites provienen del catálogo.
- Cada invitación consume un cupo en el mes de la visita. Según la PK del SQL, el mismo invitado puede tener visitas a distintas instalaciones el mismo día; cada una cuenta.
- La aplicación comprueba cuenta, estado, vigencia, fechas e instalación activa antes de registrar visitas. La invitación puede tener id_reserva nulo; la integración de reservas corresponde al otro backend.
- Las operaciones de altas usan transacciones y bloqueos `SELECT FOR UPDATE` para que dos peticiones no consuman simultáneamente el último cupo. Otros módulos que escriban estas mismas entidades deben coordinar el mismo orden de bloqueos: socio → tipo → membresía. Los triggers originales de cupos por sí solos no serializan todos los escritores externos.
- El historial lo crea exclusivamente el trigger. `history_context` pasa cedula_admin/motivo con `set_config(..., true)` dentro de la transacción; no quedan en la conexión al confirmar. Los cambios directos por SQL sin contexto conservan actor/motivo nulos.
- La inscripción inicial propone 365 días; el SQL solo exige renovación posterior a inscripción. Administración puede ajustar fechas. Los valores del catálogo original se conservan.

## Conexión

Se configura con `.env` (excluido de Git) mediante DATABASE_URL o DB_*. Las opciones de psycopg desactivan sentencias preparadas y cursores de servidor para facilitar conexiones con pool. Usar el endpoint PostgreSQL del proveedor, no una URL de API HTTP. SSL se configura con sslmode en la URL o DB_SSLMODE; para conexión remota, usa lo requerido por tu proveedor.

## Integración Backend 2

Se conservaron los modelos del repositorio para reservas, cargos, instalaciones, bloqueos y notificaciones, junto con sus migraciones. Las rutas del Backend 2 siguen mostrando integración pendiente hasta que su responsable conecte sus vistas.

La identidad autenticada es accounts.User o accounts.Administrator. Los modelos originales referencian socios.Socio o administradores.Administrador, que consultan las mismas tablas pero son clases Python diferentes. Asigna las claves al integrar una reserva, por ejemplo `reserva.socio_id = request.user.pk` después de verificar que sea una cuenta de socio; no asignes directamente request.user a una FK que espera socios.Socio. Para un administrador se aplica la misma regla a admin_id.

Ejemplo de resolución explícita si se necesita la instancia original: `Socio.objects.get(pk=request.user.pk)`. La cédula por sí sola no determina si una cuenta es administrativa; comprueba el tipo y los permisos primero.

El modelo completo de instalaciones del repositorio se usa directamente, con tipo_id para codigo_tipo y el campo FechaHoraLocalField para bloqueos. No se han reemplazado esos modelos por un catálogo mínimo. Las operaciones compartidas sobre membresías/invitaciones deben usar los servicios de Backend 1 o respetar sus transacciones y orden de bloqueos.
