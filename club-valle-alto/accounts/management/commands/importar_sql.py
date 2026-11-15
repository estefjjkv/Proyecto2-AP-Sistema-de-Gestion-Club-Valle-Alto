from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Comando antiguo deshabilitado: el esquema pertenece a core."
    def handle(self, **options):
        raise CommandError("Use python manage.py migrate. core/0001_esquema_inicial importa el SQL una sola vez. No lo importe por separado.")
