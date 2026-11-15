"""Pruebas de integración: una BD nueva y desechable, nunca la base configurada."""
import uuid
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from django.test.runner import DiscoverRunner


class SQLTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        if self.parallel > 1 or self.keepdb:
            raise RuntimeError("Esta suite usa una base SQL aislada por ejecución; no use --parallel ni --keepdb.")
        original = connection.settings_dict["NAME"]
        temporary = "test_backend1_" + uuid.uuid4().hex[:12]
        # El identificador solo contiene un prefijo constante y hex generado localmente.
        with connection._nodb_cursor() as cursor:
            cursor.execute(f'CREATE DATABASE "{temporary}"')
        connection.close()
        settings.DATABASES["default"]["NAME"] = temporary
        connection.settings_dict["NAME"] = temporary
        try:
            call_command("migrate", verbosity=0, interactive=False)
        except Exception:
            connection.creation.destroy_test_db(original, verbosity=0)
            raise
        return [(connection, original, True)]
