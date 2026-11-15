#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "Copie .env.example a .env y complete la conexión PostgreSQL que le entregue su compañero."
  echo "Comando: cp .env.example .env"
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Se necesita Python 3.10 o superior"'
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py preparar_base
if ! .venv/bin/python manage.py shell -c 'from accounts.models import Administrator; import sys; sys.exit(0 if Administrator.objects.filter(activo=True, rol_id="GENERAL").exists() else 1)'; then
  echo "Cree su administrador GENERAL. La contraseña no se muestra mientras escribe."
  .venv/bin/python manage.py crear_administrador
fi
echo "Abra http://127.0.0.1:${CLUB_PORT:-8000}/usuarios/login/"
echo "Para el administrador, elija Personal administrativo. Ctrl+C detiene el servidor."
exec .venv/bin/python manage.py runserver "127.0.0.1:${CLUB_PORT:-8000}"
