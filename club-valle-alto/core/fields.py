import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone


class FechaHoraLocalField(models.DateTimeField):
    """
    Columna `timestamp` SIN zona horaria, en hora local del club (TIME_ZONE).

    Se usa en bloqueo_instalacion.inicio/fin. Esas columnas se comparan en la
    base contra reserva.fecha + hora_inicio (hora local), así que deben
    guardarse en hora local y no en UTC.

    Un DateTimeField normal, con USE_TZ = True, enviaría la hora en UTC y el
    bloqueo quedaría corrido 6 horas.

    - Al guardar: un datetime aware se convierte a hora local "naive".
    - Al leer: se devuelve aware en la zona del club.

    Nota: para filtrar use rangos (inicio__lt=..., fin__gt=...). Las
    transformaciones __date / __hour asumen timestamptz y pueden fallar
    cerca de la medianoche.
    """

    def db_type(self, connection):
        return 'timestamp'

    def get_prep_value(self, value):
        value = self.to_python(models.Field.get_prep_value(self, value))
        if isinstance(value, datetime.datetime) and timezone.is_aware(value):
            value = timezone.make_naive(value, timezone.get_default_timezone())
        return value

    def from_db_value(self, value, expression, connection):
        if value is not None and settings.USE_TZ and timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_default_timezone())
        return value
