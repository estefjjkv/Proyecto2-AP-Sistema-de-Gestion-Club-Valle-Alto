import json
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand,CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

class Command(BaseCommand):
    help = "Aplica las migraciones del equipo y del backend; detecta un SQL importado sin historial."
    def handle(self,**options):
        if connection.vendor!='postgresql':raise CommandError('Se requiere PostgreSQL.')
        applied=MigrationRecorder(connection).applied_migrations()
        with connection.cursor() as cursor:
            tables=set(connection.introspection.table_names(cursor))
        if ('core','0001_esquema_inicial') not in applied and tables & set(json.loads((settings.BASE_DIR/'database/esquema_compatible.json').read_text(encoding='utf-8'))['tables']):
            raise CommandError('La base contiene tablas del club pero no registra core/0001. No se importó ni migró nada. Ejecute registrar_esquema_existente para comprobar compatibilidad; consulte docs/MIGRACIONES_REPOSITORIO.md.')
        call_command('migrate',interactive=False,verbosity=options['verbosity'])
        call_command('verificar_base',verbosity=options['verbosity'])
