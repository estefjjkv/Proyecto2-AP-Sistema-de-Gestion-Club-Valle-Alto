from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from estado_cuenta.services import generar_estados, nombre_periodo


class Command(BaseCommand):
    help = "Genera los estados de cuenta y cuotas de membresía del mes (por defecto, el actual). Programar el día 1 de cada mes."

    def add_arguments(self, parser):
        parser.add_argument("--periodo", help="Mes a generar en formato AAAA-MM.")

    def handle(self, *args, periodo=None, **options):
        try:
            mes = date.fromisoformat(periodo + "-01") if periodo else timezone.localdate().replace(day=1)
        except ValueError:
            raise CommandError("Use el formato AAAA-MM, por ejemplo 2026-11.")
        cuotas = generar_estados(mes)
        self.stdout.write(self.style.SUCCESS(f"Periodo {nombre_periodo(mes)}: {cuotas} cuota(s) nueva(s)."))
