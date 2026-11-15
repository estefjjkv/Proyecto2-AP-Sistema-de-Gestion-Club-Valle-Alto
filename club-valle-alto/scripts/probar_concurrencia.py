"""Crea una base PostgreSQL temporal y ejecuta las pruebas de concurrencia."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings")
from django.core.management import execute_from_command_line
execute_from_command_line(["manage.py","test","guests.tests_concurrency","--noinput"])
