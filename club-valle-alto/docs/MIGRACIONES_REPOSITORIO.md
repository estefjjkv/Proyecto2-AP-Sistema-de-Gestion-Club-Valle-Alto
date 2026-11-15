# Integración de las migraciones del equipo

## Qué se conservó

Todas las migraciones originales recibidas en el ZIP permanecen idénticas: core/0001_esquema_inicial, core/0002_initial y las 0001_initial de administradores, socios, usuarios, membresias, invitados, instalaciones, reservas, estado_cuenta y notificaciones. Se conservaron sus modelos, incluidos los de los módulos del otro backend y los campos de hora local.

El SQL activo es **core/sql/club_valle_alto.sql**, idéntico al del repositorio recibido. La versión anterior del SQL independiente no se usa. El archivo de ejemplo para crear usuario/BD contiene un marcador de contraseña que debe reemplazarse; no se ejecuta automáticamente.

## Qué se integró

Se mantienen accounts, memberships y guests como implementación del Backend 1. Sus modelos de negocio no administrados consultan las mismas tablas que los modelos del equipo. No se crean copias de socio, membresia o invitacion.

Las migraciones de soporte del backend crean auditoría de cuentas e ingresos, agregan RECEPCION y completan el historial con actor/motivo. Ahora dependen explícitamente de core/0001 para garantizar que el SQL exista primero. La nueva core/0003 alinea el valor predeterminado de fecha_cambio con clock_timestamp para bases creadas con el SQL anterior.

El repositorio ya corregía now() por clock_timestamp en el historial. La función de soporte añade administrador/motivo y una fecha estrictamente creciente. Solo el trigger inserta el historial; no se generan entradas duplicadas desde Python.

## Caso A: base PostgreSQL vacía

Configura `.env` y ejecuta `bash iniciar.sh`. `preparar_base` ejecuta las migraciones, incluyendo la creación del esquema por core. No importes el SQL antes.

La base PostgreSQL debe existir y la cuenta debe poder crear sus tablas y btree_gist. El proyecto no crea automáticamente usuarios ni bases de PostgreSQL.

## Caso B: tu compañero ya ejecutó migrate

Configura `.env` apuntando a esa base y ejecuta `bash iniciar.sh`. Django reconoce core/0001 y las migraciones existentes por sus nombres y aplica las pendientes. No vuelve a ejecutar el SQL inicial. Se comprobó este recorrido con cuentas de socio y administrador preexistentes, conservando sus contraseñas y datos.

Las cuentas en las tablas socio y administrador se usan directamente. Un superusuario creado por el Django admin original en auth_user no se convierte en administrador del club: se necesita una cuenta en administrador. Las sesiones de la autenticación anterior pueden requerir iniciar sesión de nuevo.

## Caso C: se importó SQL a mano, o se usó la entrega PostgreSQL anterior

El arranque detecta tablas sin el registro de core/0001 y se detiene. No uses --fake de forma indiscriminada ni borres django_migrations. Con el entorno virtual activado:

```bash
source .venv/bin/activate
python manage.py registrar_esquema_existente
```

Este comando solo lee: compara columnas, tipos, nulabilidad, restricciones, índices, triggers y presencia de funciones con la referencia estructural del SQL recibido. Si encuentra diferencias, no registra nada y requiere revisión del responsable de la base. La comprobación no audita el código interno de cada función ni los datos del catálogo; deben proceder del SQL conocido del equipo. Diferencias de versión del motor o personalizaciones del esquema también pueden necesitar revisión.

Si devuelve **Estructura compatible** y corresponde a la base donde ya importaste el SQL, registra únicamente esa migración inicial:

```bash
python manage.py registrar_esquema_existente --confirmar
python manage.py preparar_base
bash iniciar.sh
```

`--confirmar` añade el registro de core/0001 en django_migrations; no importa SQL ni borra datos. Las otras migraciones se ejecutan normalmente. Este recorrido se verificó contra la entrega PostgreSQL anterior.

## Para incorporarlo al repositorio Git

Usa el proyecto completo integrado. Dentro del repositorio del equipo, su código corresponde a la carpeta `club-valle-alto`; copia allí el contenido de `club-valle-alto-integrado`, conservando el `.env` local fuera de Git. Revisa el diff con el equipo antes de publicarlo. No copies un entorno virtual ni bases locales.

Las migraciones originales de instalaciones tienen el mismo nombre que una migración mínima de la entrega anterior. Se conserva la versión completa del repositorio: ambas eran managed=False y no creaban tablas. El estado resultante fue comprobado con makemigrations --check.

No ejecutes `migrate core zero` para solucionar conflictos: el reverso original elimina las tablas del club. El archivo drop se conserva porque forma parte de la migración original, no como paso de instalación.
