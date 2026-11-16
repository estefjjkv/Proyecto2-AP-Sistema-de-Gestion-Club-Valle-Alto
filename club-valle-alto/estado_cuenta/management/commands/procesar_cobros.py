from django.core.management.base import BaseCommand

from estado_cuenta.services import procesar_recordatorios


class Command(BaseCommand):
    help = "Marca cargos vencidos y envía recordatorios de pago vencido y por vencer. Programar a diario."

    def handle(self, *args, **options):
        vencidos, por_vencer = procesar_recordatorios()
        self.stdout.write(self.style.SUCCESS(
            f"Avisos de pago vencido: {vencidos} socio(s). Avisos de pago por vencer: {por_vencer} socio(s)."))
