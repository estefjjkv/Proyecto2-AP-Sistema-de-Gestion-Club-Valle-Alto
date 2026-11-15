from django.core.management.base import BaseCommand,CommandError
from django.db import transaction,connection
from django.db.migrations.recorder import MigrationRecorder
from accounts.schema_compat import verify_existing_schema

class Command(BaseCommand):
    help = "Comprueba la estructura del SQL instalado. --confirmar registra core/0001 sin repetir el SQL."
    def add_arguments(self,parser):
        parser.add_argument('--confirmar',action='store_true')
    def handle(self,**options):
        recorder=MigrationRecorder(connection)
        if ('core','0001_esquema_inicial') in recorder.applied_migrations():
            self.stdout.write('core/0001 ya está registrada; no se modificó nada.');return
        with transaction.atomic():
            verify_existing_schema()
            if options['confirmar']:
                recorder.record_applied('core','0001_esquema_inicial')
                self.stdout.write(self.style.SUCCESS('Esquema compatible registrado; no se recrearon tablas ni se modificaron datos del club. Ejecute preparar_base.'))
            else:
                self.stdout.write('Estructura compatible. Si corresponde a la base que importó el SQL previamente, ejecute este comando con --confirmar para registrar core/0001. No se modificó nada.')
