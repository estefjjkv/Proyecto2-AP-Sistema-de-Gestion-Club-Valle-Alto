from django.core.management.base import BaseCommand

from reservas.services import finalizar_reservas


class Command(BaseCommand):
    help = ("Pasa a FINALIZADA las reservas confirmadas que ya terminaron y cancela las pendientes "
            "que no se confirmaron antes de iniciar. Programar periódicamente (por ejemplo, cada hora).")

    def handle(self, *args, **options):
        finalizadas, canceladas = finalizar_reservas()
        self.stdout.write(self.style.SUCCESS(f"Reservas finalizadas: {finalizadas}. Pendientes canceladas: {canceladas}."))
