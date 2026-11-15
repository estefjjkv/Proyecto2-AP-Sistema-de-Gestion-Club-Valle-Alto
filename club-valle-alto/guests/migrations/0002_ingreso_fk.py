from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [("core", "0001_esquema_inicial"), ("guests", "0001_initial")]
    operations = [migrations.RunSQL(
        "ALTER TABLE backend1_ingreso_invitado ADD CONSTRAINT backend1_ingreso_visita_fk FOREIGN KEY (socio,invitado,fecha_visita,instalacion) REFERENCES invitacion(cedula_socio,cedula_invitado,fecha_visita,codigo_instalacion) ON DELETE CASCADE",
        "ALTER TABLE backend1_ingreso_invitado DROP CONSTRAINT backend1_ingreso_visita_fk",
    )]
