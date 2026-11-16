from datetime import date

from django import forms
from django.utils import timezone

from socios.models import Socio
from .models import Cargo
from .services import colones, nombre_periodo, siguiente_mes


def periodos_recientes(atras=12, adelante=1):
    """[(date, 'Noviembre 2026'), ...] desde `adelante` meses en el futuro hasta `atras` meses atrás."""
    mes = timezone.localdate().replace(day=1)
    for _ in range(adelante):
        mes = siguiente_mes(mes)
    salida = []
    for _ in range(atras + adelante + 1):
        salida.append((mes, nombre_periodo(mes).capitalize()))
        mes = date(mes.year - 1, 12, 1) if mes.month == 1 else date(mes.year, mes.month - 1, 1)
    return salida


class PeriodoField(forms.TypedChoiceField):
    def __init__(self, *args, adelante=1, **kwargs):
        kwargs.setdefault("coerce", date.fromisoformat)
        super().__init__(*args, **kwargs)
        self.choices = [(d.isoformat(), texto) for d, texto in periodos_recientes(adelante=adelante)]


class GenerarForm(forms.Form):
    periodo = PeriodoField(label="Periodo")


class FiltroForm(forms.Form):
    ESTADOS = [("", "Todos"), ("PAGADO", "Pagado"), ("PENDIENTE", "Pendiente"), ("VENCIDO", "Vencido")]
    q = forms.CharField(label="Buscar socio", required=False,
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Nombre o cédula"}))
    periodo = PeriodoField(label="Periodo")
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS, required=False)


class CargoChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, cargo):
        return f"{cargo.descripcion} · {colones(cargo.monto)} · vence {cargo.fecha_limite_pago:%d/%m/%Y}"


class SocioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, socio):
        return f"{socio.nombre_completo} · {socio.cedula}"


class PagoForm(forms.Form):
    socio = SocioChoiceField(queryset=Socio.objects.none(), label="Socio")
    cargos = CargoChoiceField(queryset=Cargo.objects.none(), label="Cargos que cubre el pago",
                              widget=forms.CheckboxSelectMultiple)
    fecha_pago = forms.DateField(label="Fecha de pago", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    referencia = forms.CharField(label="Referencia u observación", max_length=200, required=False,
                                 widget=forms.TextInput(attrs={"placeholder": "Ej.: transferencia 123456"}))

    def __init__(self, *args, socio_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        con_deuda = Cargo.objects.exclude(estado_id="PAGADO").values("socio_id")
        self.fields["socio"].queryset = Socio.objects.filter(cedula__in=con_deuda).order_by("nombre_completo")
        self.fields["cargos"].queryset = (Cargo.objects.filter(socio_id=socio_id).exclude(estado_id="PAGADO")
                                          .order_by("periodo", "fecha_limite_pago", "pk") if socio_id else Cargo.objects.none())
        self.fields["fecha_pago"].widget.attrs["max"] = timezone.localdate().isoformat()
