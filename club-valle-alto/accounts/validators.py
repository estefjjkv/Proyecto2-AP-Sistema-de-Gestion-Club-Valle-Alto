import re
from django.core.exceptions import ValidationError
from django.utils import timezone


def normalize_id(value):
    value = re.sub(r"[\s-]", "", value).upper()
    if not re.fullmatch(r"[A-Z0-9]{5,20}", value):
        raise ValidationError("Use entre 5 y 20 letras o números para la identificación.")
    return value


def normalize_phone(value):
    value = re.sub(r"[\s()-]", "", value)
    if re.fullmatch(r"[0-9]{8}", value):
        value = "+506" + value
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
        raise ValidationError("Ingrese 8 dígitos de Costa Rica o un número internacional, por ejemplo +50688887777.")
    return value


def past_birth(value):
    if value and value >= timezone.localdate():
        raise ValidationError("La fecha de nacimiento debe ser anterior a hoy.")
