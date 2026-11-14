from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Esquema de la base de datos (migración SQL) y catálogos compartidos."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Base de datos y catálogos'
