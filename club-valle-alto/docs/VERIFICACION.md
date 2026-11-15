# Verificación — 14 de noviembre de 2026

Entorno utilizado: Python 3.14, Django 5.2.19, psycopg 3.3.9 y PostgreSQL 18.6 real, local y aislado. El servidor de pruebas se proporcionó mediante embedded-postgres; no es una dependencia de ejecución del proyecto ni se incluye en el ZIP.

## Resultados

- Creación de una base vacía a través de core/0001 del repositorio, incluida btree_gist y sus triggers/vistas.
- Aplicación de migraciones de soporte, sin tablas duplicadas para entidades de negocio.
- Comprobación de todas las columnas mapeadas por los modelos no administrados.
- `manage.py check`: sin problemas.
- `manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- **63 pruebas automatizadas aprobadas**, incluidas 4 pruebas de concurrencia sobre conexiones PostgreSQL independientes.

## Cobertura

Registro y perfil, claves naturales, separación de identidades con el mismo correo/cédula, hashes, bloqueo persistente de intentos y expiración, suspensión/desactivación y revocación de sesión, permisos tomados del SQL, creación de administradores, protección ante pérdida de acceso propio, cambio de contraseña administrativa y conservación de la sesión propia.

Recuperación de socios: envío simulado, token guardado como hash, expiración, uso único, invalidación de enlaces anteriores tras el restablecimiento, fallo SMTP controlado y recorrido HTTP completo. CSRF y logout exclusivamente por POST.

Membresías: cuotas/límites del catálogo original, inscripción única, altas administrativas, fechas, suspensión/baja, historial sin duplicados, múltiples estados dentro de la misma transacción, autor y motivo, vencimiento por fecha, claves compuestas de beneficiarios, límites, actualización/eliminación, acceso por titular y prohibición de confundir una cuenta administrativa con un socio de igual cédula.

Invitados: escritura en invitado e invitacion, duplicados según la PK real, instalaciones distintas para un mismo invitado/día, cuota mensual y cambio de mes, no sobrescribir nombres de invitados existentes, vigencia, suspensión, auto-invitación, recepción por fecha e ingreso firmado, persistente y de un solo uso. Formularios y páginas principales probados mediante cliente HTTP Django.

Concurrencia: último cupo de invitados, último cupo de beneficiarios, inscripción única y cinco fallos simultáneos de autenticación. La suite crea y elimina una base temporal para cada ejecución.

## Límites

No se probó una conexión al servidor del compañero ni a Supabase, porque no se proporcionó una conexión. No se entregó correo por un proveedor SMTP real y no se hizo despliegue. La entrega mantiene desarrollo local por defecto. Los datos de prueba no se incluyen en el ZIP.

La verificación de esta adaptación incluye formularios y respuestas HTML mediante el cliente de pruebas; no equivale a una nueva revisión visual de todas las pantallas en todos los navegadores. La apariencia conserva el frontend integrado previamente.

Para repetir: `bash probar.sh`. La cuenta PostgreSQL de pruebas necesita crear bases y extensiones. Consulta `INSTALACION.md`.

## Verificación específica de esta integración

- Todas las migraciones originales del ZIP se conservaron byte por byte.
- Los 9 archivos models.py originales y los modelos de core se conservaron.
- Simulación de una base instalada por las migraciones del repositorio original: se crearon previamente un socio y un administrador con contraseñas hasheadas, se aplicó el backend y se verificaron login, permisos e inscripción de membresía sin cambiar sus hashes.
- Actualización desde la base de la entrega PostgreSQL anterior mediante comprobación estructural y registro de core/0001; migraciones pendientes aplicadas sin recrear tablas.
- Cuatro pruebas adicionales cubren esquema ya registrado, detención del arranque ante SQL sin historial, comprobación sin cambios, confirmación explícita y rechazo de un esquema incompleto.
- Ninguna migración fue ejecutada contra un servidor del usuario o del equipo. Las pruebas se hicieron en bases locales aisladas.
