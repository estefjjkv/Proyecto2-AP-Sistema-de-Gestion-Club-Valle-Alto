from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = "Verifica que existen las tablas y columnas originales, sin modificar datos."
    def handle(self, **options):
        if connection.vendor != "postgresql": raise CommandError("Se requiere PostgreSQL.")
        missing=[]
        with connection.cursor() as cur:
            cur.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema=current_schema()")
            columns=set(cur.fetchall())
        for model in apps.get_models():
            if model._meta.managed: continue
            for field in model._meta.local_concrete_fields:
                if field.column and (model._meta.db_table,field.column) not in columns:
                    missing.append(f"{model._meta.db_table}.{field.column}")
        if missing: raise CommandError("Faltan columnas del SQL: " + ", ".join(missing) + ". Importe database/club_valle_alto.sql solo si la base está vacía.")
        self.stdout.write(self.style.SUCCESS("Tablas y columnas compatibles con Backend 1."))
