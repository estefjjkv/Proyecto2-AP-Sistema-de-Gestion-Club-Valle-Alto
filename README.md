# Sistema de Gestión Club Valle Alto

Proyecto 2 del curso **Administración de Proyectos**: un sistema web demostrativo para administrar un club social y deportivo, con socios, membresías, invitados, reservas de instalaciones, cobros y notificaciones por correo.

El sistema tiene dos portales:

- **Portal de socios:** registro, perfil, membresía y beneficiarios, invitados, reservas y estado de cuenta.
- **Portal administrativo:** gestión de socios, membresías, administradores, recepción de invitados, instalaciones, reservas, cobros y notificaciones. Cada administrador ve solo lo que permite su rol.

## Tecnología

- **Python 3.10+ y Django 5.2:** aplicación web con plantillas del lado del servidor.
- **PostgreSQL:** base de datos. Varias reglas de negocio viven en la propia base mediante triggers y restricciones, por ejemplo que dos reservas de una misma instalación no se traslapen.

## Módulos

| Módulo | Qué permite |
|---|---|
| Registro de socios | Registro, inicio de sesión, recuperación de contraseña, perfil y gestión de cuentas (activar, suspender, desactivar) |
| Membresías | Tipos de membresía, inscripción, suspensión y baja, beneficiarios e historial de cambios |
| Invitados | Registro de invitados con límite mensual según la membresía; recepción con invitados esperados y registro de ingreso |
| Administradores | Usuarios administrativos con roles (General, Instalaciones, Cobros, Recepción) y permisos |
| Gestión de instalaciones | Instalaciones, servicios adicionales, bloqueos por mantenimiento o evento, control de ocupación y reportes de uso |
| Reservas | Solicitud con disponibilidad en vivo, confirmación por administración, modificación, cancelación, calendario semanal e historial de cambios |
| Estados de cuenta | Cuotas mensuales, cargos por servicios, registro de pagos, socios morosos y versión imprimible |
| Centro de notificaciones | Historial de correos enviados, reenvío y edición de plantillas |


## Cómo ejecutarlo

Requisitos: Python 3.10 o superior y un servidor PostgreSQL con una base vacía.

```bash
cd club-valle-alto
cp .env.example .env      # completar los datos de conexión a PostgreSQL
bash iniciar.sh           # crea el entorno, prepara la base y pide crear el administrador
```

Después, abrir http://127.0.0.1:8000/usuarios/login/ y elegir **Personal administrativo** para entrar con el administrador creado.

### Datos de demostración

Para tener información en todas las pantallas:

```bash
.venv/bin/python manage.py cargar_demo
```

El comando crea 5 socios con distintos tipos de membresía, administradores de cada rol, instalaciones con servicios, reservas en todos los estados, bloqueos, invitados, tres meses de estados de cuenta con pagos y un socio moroso, y las notificaciones correspondientes. Todas las cuentas usan la contraseña `ClubDemo2026!`; el comando muestra la lista de correos al terminar.

| Cuenta | Tipo |
|---|---|
| `maria.lopez@example.com` | Socia con membresía familiar, beneficiarios, reservas e invitados |
| `ana.vargas@example.com` | Socia con pagos atrasados (aparece en morosos) |
| `instalaciones@example.com` | Administrador de instalaciones y reservas |
| `cobros@example.com` | Administrador de cobros |
| `recepcion@example.com` | Recepción de invitados |

### Pruebas

```bash
bash probar.sh
```

Ejecuta las pruebas automáticas de todos los módulos en una base temporal, que se crea y se elimina sola.

### Tareas periódicas

En una instalación real, estos comandos se programarían para correr solos (por ejemplo, con cron). Para la demostración se pueden ejecutar a mano:

| Comando | Frecuencia sugerida | Qué hace |
|---|---|---|
| `manage.py finalizar_reservas` | Cada hora | Finaliza las reservas confirmadas que ya terminaron y cancela las pendientes que no se confirmaron |
| `manage.py procesar_cobros` | Diario | Marca cargos vencidos y envía recordatorios de pago |
| `manage.py generar_estados_cuenta` | Día 1 de cada mes | Genera las cuotas de membresía del mes |
| `manage.py actualizar_vencimientos` | Diario | Marca como vencidas las membresías cuya renovación ya pasó |

En modo de desarrollo, los correos no se envían: se imprimen en la terminal donde corre el servidor.

## Documentación adicional

Dentro de [`club-valle-alto/docs/`](club-valle-alto/docs/):

- [INSTALACION.md](club-valle-alto/docs/INSTALACION.md): instalación detallada, también en Windows.
- [INTEGRACION_BASE_DATOS.md](club-valle-alto/docs/INTEGRACION_BASE_DATOS.md): cómo se integra el esquema SQL con Django.
- [MIGRACIONES_REPOSITORIO.md](club-valle-alto/docs/MIGRACIONES_REPOSITORIO.md): qué hacer si la base ya existía.
- [VERIFICACION.md](club-valle-alto/docs/VERIFICACION.md): verificación del sistema.
