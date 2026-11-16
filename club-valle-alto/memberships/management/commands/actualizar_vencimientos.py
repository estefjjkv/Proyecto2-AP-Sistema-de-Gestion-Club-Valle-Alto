from django.core.management.base import BaseCommand
from memberships.services import expire_memberships


class Command(BaseCommand):
    help = "Marca membresías vencidas y registra su historial; ejecutar diariamente."
    def handle(self, *args, **options):
        self.stdout.write(f"Membresías actualizadas: {expire_memberships()}")
