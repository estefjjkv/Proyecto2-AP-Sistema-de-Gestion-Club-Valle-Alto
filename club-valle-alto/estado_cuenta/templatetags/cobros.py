from django import template

from estado_cuenta.services import colones as _colones, nombre_periodo

register = template.Library()


@register.filter
def colones(monto):
    """1234567.5 -> '₡1 234 568'"""
    return _colones(monto or 0)


@register.filter
def periodo(fecha):
    """date(2026, 11, 1) -> 'Noviembre 2026'"""
    return nombre_periodo(fecha).capitalize() if fecha else ""


@register.inclusion_tag("estado_cuenta/_estado.html")
def estado_badge(estado):
    return {"estado": estado}
