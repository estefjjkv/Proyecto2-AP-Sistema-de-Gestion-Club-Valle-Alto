from datetime import date, datetime, time

from django import forms
from django.utils import timezone

from core.models import CatMotivoBloqueo
from .models import Instalacion, ServicioAdicional

FECHA = {"type": "date"}
HORA = {"type": "time"}


class InstalacionForm(forms.ModelForm):
    class Meta:
        model = Instalacion
        fields = ("codigo", "nombre", "tipo", "aforo_maximo", "hora_apertura", "hora_cierre", "activa")
        labels = {"codigo": "Código", "aforo_maximo": "Aforo máximo", "hora_apertura": "Hora de apertura",
                  "hora_cierre": "Hora de cierre", "activa": "Disponible para reservas"}
        help_texts = {"codigo": "Identificador corto, por ejemplo TENIS-1. No se puede cambiar después."}
        widgets = {"hora_apertura": forms.TimeInput(attrs=HORA, format="%H:%M"),
                   "hora_cierre": forms.TimeInput(attrs=HORA, format="%H:%M")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["codigo"].disabled = True
        self.fields["aforo_maximo"].min_value = 1
        self.fields["aforo_maximo"].widget.attrs["min"] = 1

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean(self):
        data = super().clean()
        apertura, cierre = data.get("hora_apertura"), data.get("hora_cierre")
        if apertura and cierre and cierre <= apertura:
            self.add_error("hora_cierre", "La hora de cierre debe ser posterior a la de apertura.")
        return data


class ServicioForm(forms.ModelForm):
    class Meta:
        model = ServicioAdicional
        fields = ("codigo", "nombre", "descripcion", "tipo_instalacion", "precio", "activo")
        labels = {"codigo": "Código", "descripcion": "Descripción", "tipo_instalacion": "Tipo de instalación",
                  "precio": "Precio (₡)", "activo": "Disponible"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["codigo"].disabled = True
        self.fields["precio"].min_value = 0

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()


def _local(dia, hora):
    return timezone.make_aware(datetime.combine(dia, hora), timezone.get_default_timezone())


class BloqueoForm(forms.Form):
    instalacion = forms.ModelChoiceField(queryset=Instalacion.objects.order_by("nombre"), label="Instalación")
    fecha_inicio = forms.DateField(label="Fecha inicial", widget=forms.DateInput(attrs=FECHA))
    hora_inicio = forms.TimeField(label="Hora inicial", widget=forms.TimeInput(attrs=HORA))
    fecha_fin = forms.DateField(label="Fecha final", widget=forms.DateInput(attrs=FECHA))
    hora_fin = forms.TimeField(label="Hora final", widget=forms.TimeInput(attrs=HORA))
    motivo = forms.ModelChoiceField(queryset=CatMotivoBloqueo.objects.all(), label="Motivo")
    descripcion = forms.CharField(label="Descripción", max_length=300, required=False)

    def clean(self):
        data = super().clean()
        campos = ("fecha_inicio", "hora_inicio", "fecha_fin", "hora_fin")
        if all(data.get(c) for c in campos):
            data["inicio"] = _local(data["fecha_inicio"], data["hora_inicio"])
            data["fin"] = _local(data["fecha_fin"], data["hora_fin"])
            if data["fin"] <= data["inicio"]:
                raise forms.ValidationError("El final del bloqueo debe ser posterior al inicio.")
            if data["fin"] <= timezone.now():
                raise forms.ValidationError("No se pueden registrar bloqueos que ya terminaron.")
        return data


FRANJAS = [(h, f"{h:02d}:00 - {h + 1:02d}:00") for h in range(5, 23)]


class OcupacionForm(forms.Form):
    fecha = forms.DateField(label="Fecha", widget=forms.DateInput(attrs=FECHA))
    hora = forms.TypedChoiceField(label="Horario", choices=FRANJAS, coerce=int)

    def franja(self):
        hora = self.cleaned_data["hora"]
        return time(hora), time(hora + 1)


def meses_recientes(cantidad=12):
    """[(date(año, mes, 1), "octubre de 2026"), ...] desde el mes actual hacia atrás."""
    nombres = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"]
    hoy = timezone.localdate()
    año, mes, salida = hoy.year, hoy.month, []
    for _ in range(cantidad):
        salida.append((date(año, mes, 1), f"{nombres[mes - 1].capitalize()} de {año}"))
        año, mes = (año - 1, 12) if mes == 1 else (año, mes - 1)
    return salida


class ReporteForm(forms.Form):
    periodo = forms.TypedChoiceField(label="Periodo", coerce=date.fromisoformat)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periodo"].choices = [(d.isoformat(), nombre) for d, nombre in meses_recientes()]
