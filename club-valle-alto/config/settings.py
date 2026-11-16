"""
Django settings for config project - Sistema Web de Gestión para el Club Valle Alto.
"""

from pathlib import Path
import os
import secrets
from dotenv import load_dotenv
from urllib.parse import urlsplit, parse_qs, unquote

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Persistencia local sin incluir secretos en el ZIP ni en Git.
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("Configure DJANGO_SECRET_KEY para producción.")
    secret_file = BASE_DIR / ".local-secret"
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(50))
        secret_file.chmod(0o600)
    SECRET_KEY = secret_file.read_text().strip()



ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]").split(",")

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'accounts',
    'memberships',
    'guests',
    # Apps del Club Valle Alto
    'usuarios',
    'socios',
    'membresias',
    'invitados',
    'instalaciones',
    'reservas',
    'estado_cuenta',
    'notificaciones',
    'administradores',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.AccessMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Use DATABASE_URL del proveedor o las variables DB_* del archivo .env.
raw_url = os.environ.get("DATABASE_URL", "")
if raw_url:
    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL debe ser de PostgreSQL.")
    query = parse_qs(parsed.query)
    db = {"NAME": unquote(parsed.path.lstrip("/")), "USER": unquote(parsed.username or ""),
          "PASSWORD": unquote(parsed.password or ""), "HOST": parsed.hostname, "PORT": parsed.port or 5432}
    sslmode = query.get("sslmode", [os.environ.get("DB_SSLMODE", "require")])[0]
else:
    db = {"NAME": os.environ.get("DB_NAME", "club_valle_alto"), "USER": os.environ.get("DB_USER", "postgres"),
          "PASSWORD": os.environ.get("DB_PASSWORD", ""), "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
          "PORT": os.environ.get("DB_PORT", "5432")}
    sslmode = os.environ.get("DB_SSLMODE", "prefer")
DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", **db,
    "CONN_MAX_AGE": 0, "DISABLE_SERVER_SIDE_CURSORS": True,
    "OPTIONS": {"sslmode": sslmode, "prepare_threshold": None}}}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-cr'

TIME_ZONE = 'America/Costa_Rica'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.SocioBackend", "accounts.backends.AdminBackend"]
LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "socios:inicio"
LOGOUT_REDIRECT_URL = "usuarios:login"
LOGIN_FAILURE_LIMIT = 5
LOGIN_LOCK_MINUTES = 15
PASSWORD_RESET_TIMEOUT = 3600
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Club Valle Alto <no-reply@example.com>")
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
STATIC_ROOT = BASE_DIR / "staticfiles"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

MEMBERSHIP_DURATION_DAYS = 365

TEST_RUNNER = "config.testing.SQLTestRunner"
