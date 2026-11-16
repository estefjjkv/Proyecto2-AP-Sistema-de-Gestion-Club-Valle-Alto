from django.db import migrations

class Migration(migrations.Migration):
    dependencies=[('core','0002_initial'),('memberships','0002_historial_y_recepcion')]
    operations=[migrations.RunSQL(
        'ALTER TABLE historial_membresia ALTER COLUMN fecha_cambio SET DEFAULT clock_timestamp()',
        migrations.RunSQL.noop,
    )]
