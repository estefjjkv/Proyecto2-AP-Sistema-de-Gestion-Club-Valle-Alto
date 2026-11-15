# Instalación y configuración

## Requisitos

Python 3.10 o superior y un servidor PostgreSQL disponible. El proyecto usa Django 5.2.19 y psycopg 3. El servidor puede estar en la computadora o en un proveedor remoto; el backend se conecta por el protocolo PostgreSQL.

Pide a tu compañero el nombre de la base, servidor, puerto, usuario, contraseña y requisito de SSL, o su cadena PostgreSQL completa. No necesitas que mande sus credenciales por este chat. Las claves de la API de Supabase no sustituyen una conexión PostgreSQL. Si proporciona una URL, los caracteres especiales de usuario/contraseña deben ir codificados para URL; usar los campos DB_* separados evita esa codificación.

## Instalación con las migraciones integradas

Desde la carpeta con manage.py:

```bash
cp .env.example .env
# Completa .env en Visual Studio Code.
bash iniciar.sh
```

Para hacerlo manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py preparar_base
python manage.py crear_administrador
python manage.py runserver
```

En Windows, usa `py -m venv .venv` y `.venv\Scripts\Activate.ps1`, seguido por los comandos python anteriores.

`preparar_base` ejecuta migrate tanto sobre una base vacía como sobre una base con las migraciones originales aplicadas. El comando antiguo importar_sql está deshabilitado: core/0001 es el único punto de importación del SQL.

Si la base se creó importando SQL manualmente o con la entrega PostgreSQL anterior, sigue el caso C de MIGRACIONES_REPOSITORIO.md. El arranque no intentará crear tablas repetidas.

La cuenta de migraciones debe poder crear tablas/extensiones y reemplazar fn_historial_membresia. El responsable de la base puede aplicar las migraciones con su cuenta de mantenimiento y usar después una cuenta de aplicación de menores permisos.

## Datos de prueba opcionales

```bash
python manage.py preparar_demo
```

Crea tres instalaciones identificadas con prefijo DEMO- si no existen. No crea socios ni contraseñas, ni reemplaza catálogos o cuotas. Si ya tienen instalaciones reales, no es necesario.

## Correo de recuperación

El modo predeterminado imprime el correo en la terminal. Para enviar correo real, configura en `.env`:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.tu-proveedor.example
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=tu_usuario
EMAIL_HOST_PASSWORD=tu_clave_privada
DEFAULT_FROM_EMAIL=Club Valle Alto <correo-verificado@tu-dominio.example>
SITE_URL=http://127.0.0.1:8000
```

Usa los valores reales de tu proveedor. Reinicia el servidor después de cambiarlos. SITE_URL debe apuntar a la dirección que abrirá quien reciba el enlace. Una dirección 127.0.0.1 solo funciona en la misma computadora.

La recuperación pública por correo corresponde a socios porque `token_recuperacion` referencia exclusivamente `socio`. Un GENERAL puede cambiar contraseñas de administradores desde Administradores → Contraseña. Para crear otra cuenta GENERAL desde la terminal usa `crear_administrador`.

## Puerto ocupado, reinicios y vencimientos

Para detener el servidor, Ctrl+C. Para iniciarlo otra vez, `bash iniciar.sh`. Para usar otro puerto:

```bash
CLUB_PORT=8001 SITE_URL=http://127.0.0.1:8001 bash iniciar.sh
```

El estado efectivo de la membresía siempre comprueba su fecha. Para guardar explícitamente VENCIDA y su historial, ejecutar diariamente:

```bash
python manage.py actualizar_vencimientos
```

No se instala automáticamente un programador de tareas. El inicio del servidor tampoco altera masivamente estados.

## Pruebas

```bash
bash probar.sh
```

La suite crea una nueva base con nombre aleatorio `test_backend1_*`, importa el SQL y aplica migraciones, ejecuta las pruebas y elimina esa base. No vacía la base indicada en `.env`. El usuario PostgreSQL de pruebas requiere CREATEDB y permisos para la extensión. No usar `--keepdb` ni `--parallel`. En un proveedor que no permita crear bases adicionales, configura un PostgreSQL local de pruebas mediante variables DB_* y deja DATABASE_URL vacía.

## Publicación

Esta entrega usa el servidor de desarrollo local. Para publicar deben configurar HTTPS, un servidor WSGI, archivos estáticos, DJANGO_DEBUG=0, un DJANGO_SECRET_KEY privado y DJANGO_ALLOWED_HOSTS con el dominio real. No se ha realizado ningún despliegue ni configuración remota.
