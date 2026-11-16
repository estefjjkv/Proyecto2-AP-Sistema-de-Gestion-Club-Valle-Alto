"""
Crea el esquema completo de la base de datos del Club Valle Alto.

Ejecuta core/sql/club_valle_alto.sql tal cual (tablas, catálogos con datos,
triggers, restricciones EXCLUDE, columna generada y vistas). Los modelos de
todas las apps usan managed = False, así que esta es la ÚNICA migración que
modifica la estructura de la base.

Importante: no edite club_valle_alto.sql para cambiar el esquema de una base
que ya existe. Cree una migración nueva en core con migrations.RunSQL(...).
"""
from pathlib import Path

from django.db import migrations

SQL_DIR = Path(__file__).resolve().parent.parent / 'sql'


def _leer_sql(nombre):
    # encoding explícito: en Windows el default (cp1252) dañaría las tildes
    return (SQL_DIR / nombre).read_text(encoding='utf-8')


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # Se pasa como lista de UN elemento para que Django envíe el script
        # completo en una sola ejecución, sin partirlo por ';' (los cuerpos
        # $$ ... $$ de las funciones PL/pgSQL contienen ';').
        migrations.RunSQL(
            sql=[_leer_sql('club_valle_alto.sql')],
            reverse_sql=[_leer_sql('club_valle_alto_drop.sql')],
        ),
    ]
