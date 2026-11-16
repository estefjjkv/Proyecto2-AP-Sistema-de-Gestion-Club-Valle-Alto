"""
Servicios de estado de cuenta usados por otros módulos.

La generación mensual, el registro de pagos y los recordatorios se completan
en la fase de cobros; aquí está lo mínimo que necesitan las reservas.
"""
from datetime import date

from .models import EstadoCuenta

# Día del mes siguiente al periodo en que vence el pago (ajustar al reglamento).
DIA_LIMITE_PAGO = 10


def limite_pago(periodo):
    año, mes = (periodo.year + 1, 1) if periodo.month == 12 else (periodo.year, periodo.month + 1)
    return date(año, mes, DIA_LIMITE_PAGO)


def obtener_estado_cuenta(socio_id, fecha):
    """Estado de cuenta del socio para el mes de `fecha`; lo crea si no existe."""
    periodo = fecha.replace(day=1)
    estado, _ = EstadoCuenta.objects.get_or_create(
        socio_id=socio_id, periodo=periodo, defaults={"fecha_limite_pago": limite_pago(periodo)})
    return estado
