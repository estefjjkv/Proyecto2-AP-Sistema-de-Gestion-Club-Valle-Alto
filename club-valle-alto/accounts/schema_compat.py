"""Inspección estructural previa a adoptar un esquema SQL ya instalado."""
import json
from pathlib import Path
from django.conf import settings
from django.db import connection
from django.core.management.base import CommandError


def snapshot(tables):
    with connection.cursor() as cursor:
        cursor.execute("""SELECT c.relname,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull
            FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute a ON a.attrelid=c.oid
            WHERE n.nspname=current_schema() AND c.relname=ANY(%s)
            AND a.attnum>0 AND NOT a.attisdropped ORDER BY c.relname,a.attnum""",[tables])
        columns=[list(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT c.relname,con.conname,pg_get_constraintdef(con.oid)
            FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=current_schema() AND c.relname=ANY(%s) AND con.contype <> 'n'
            ORDER BY c.relname,con.conname""",[tables])
        constraints=[list(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid)
            FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname=current_schema() AND c.relname=ANY(%s) AND NOT t.tgisinternal
            ORDER BY c.relname,t.tgname""",[tables])
        triggers=[list(row) for row in cursor.fetchall()]
        cursor.execute("""SELECT t.relname,i.relname,pg_get_indexdef(i.oid)
            FROM pg_index x JOIN pg_class t ON t.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname=current_schema()
            AND t.relname=ANY(%s) ORDER BY t.relname,i.relname""",[tables])
        indexes=[list(row) for row in cursor.fetchall()]
    return dict(columns=columns,constraints=constraints,triggers=triggers,indexes=indexes)


def verify_existing_schema():
    reference=json.loads((settings.BASE_DIR/'database/esquema_compatible.json').read_text(encoding='utf-8'))
    actual=snapshot(reference['tables'])
    for category in ['columns','constraints','triggers','indexes']:
        if actual[category] != reference[category]:
            raise CommandError(f"El esquema existente difiere en {category}. No se registró core ni se importó SQL. Revise la diferencia con el responsable de la base.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT routine_name FROM information_schema.routines WHERE routine_schema=current_schema()")
        functions={row[0] for row in cursor.fetchall()}
        if not set(reference['functions'])<=functions:
            raise CommandError("Faltan funciones del SQL. No se registró ninguna migración.")
