from io import StringIO
from django.test import TestCase
from django.core.management import call_command,CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

class SchemaIntegrationTests(TestCase):
    def setUp(self):self.recorder=MigrationRecorder(connection)
    def unregister(self):self.recorder.record_unapplied('core','0001_esquema_inicial')
    def test_existing_registered_schema_is_noop(self):
        before=set(self.recorder.applied_migrations())
        call_command('registrar_esquema_existente',confirmar=True,stdout=StringIO())
        self.assertEqual(before,set(self.recorder.applied_migrations()))
    def test_unregistered_sql_stops_normal_start(self):
        self.unregister()
        with self.assertRaisesMessage(CommandError,'no registra core/0001'):call_command('preparar_base',stdout=StringIO())
        self.assertNotIn(('core','0001_esquema_inicial'),self.recorder.applied_migrations())
    def test_check_only_does_not_register_and_confirm_does(self):
        self.unregister()
        call_command('registrar_esquema_existente',stdout=StringIO())
        self.assertNotIn(('core','0001_esquema_inicial'),self.recorder.applied_migrations())
        call_command('registrar_esquema_existente',confirmar=True,stdout=StringIO())
        self.assertIn(('core','0001_esquema_inicial'),self.recorder.applied_migrations())
    def test_incomplete_schema_is_not_registered(self):
        self.unregister()
        with connection.cursor() as cursor:cursor.execute('ALTER TABLE socio DROP COLUMN direccion')
        with self.assertRaisesMessage(CommandError,'difiere en columns'):call_command('registrar_esquema_existente',confirmar=True,stdout=StringIO())
        self.assertNotIn(('core','0001_esquema_inicial'),self.recorder.applied_migrations())
