#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
# Incluye 4 pruebas con conexiones simultáneas; crea y elimina una BD test_backend1_*.
.venv/bin/python manage.py test accounts memberships guests instalaciones notificaciones --verbosity 2 --noinput
