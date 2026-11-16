from datetime import time
from django.core.management.base import BaseCommand
from instalaciones.models import Instalacion

class Command(BaseCommand):
    help = "Agrega 3 instalaciones de demostración si no existen; no cambia las cuotas ni las cuentas."
    def handle(self, **options):
        for code,name,kind,capacity in [("DEMO-PISCINA","Piscina (demostración)","PISCINA",30),("DEMO-TENIS","Cancha de tenis (demostración)","TENIS",4),("DEMO-GOLF","Campo de golf (demostración)","GOLF",40)]:
            Instalacion.objects.get_or_create(codigo=code,defaults={"nombre":name,"tipo_id":kind,"aforo_maximo":capacity,"hora_apertura":time(6),"hora_cierre":time(20),"activa":True})
        self.stdout.write(self.style.SUCCESS("Instalaciones de demostración disponibles."))
