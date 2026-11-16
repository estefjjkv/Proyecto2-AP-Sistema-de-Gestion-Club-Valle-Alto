import re

from django import forms

from core.models import CatTipoNotificacion
from estado_cuenta.forms import PeriodoField
from .models import PlantillaNotificacion

# Marcadores que notificaciones.services.notificar sabe reemplazar.
MARCADORES = {"nombre": "Nombre completo del socio", "detalle": "Detalle del evento (reserva, periodo, montos…)"}
PATRON = re.compile(r"{{\s*([^{}]*?)\s*}}")


class FiltroForm(forms.Form):
    ESTADOS = [("", "Todos"), ("ENVIADA", "Enviada"), ("PENDIENTE", "Pendiente"), ("FALLIDA", "Fallida")]
    q = forms.CharField(label="Buscar destinatario", required=False,
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Correo, nombre o cédula"}))
    tipo = forms.ModelChoiceField(label="Tipo de notificación", queryset=CatTipoNotificacion.objects.order_by("descripcion"),
                                  required=False, empty_label="Todas")
    periodo = PeriodoField(label="Periodo", adelante=0, required=False)
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["periodo"].choices = [("", "Todos")] + list(self.fields["periodo"].choices)


class PlantillaForm(forms.ModelForm):
    class Meta:
        model = PlantillaNotificacion
        fields = ("asunto", "cuerpo")
        labels = {"asunto": "Asunto del correo", "cuerpo": "Cuerpo del mensaje"}
        widgets = {"cuerpo": forms.Textarea(attrs={"rows": 7})}

    def _validar(self, campo):
        texto = self.cleaned_data[campo]
        desconocidos = sorted({m for m in PATRON.findall(texto) if m not in MARCADORES})
        if desconocidos:
            raise forms.ValidationError("Marcadores no válidos: %s. Use solo %s." % (
                ", ".join("{{%s}}" % m for m in desconocidos), ", ".join("{{%s}}" % m for m in MARCADORES)))
        # Normaliza «{{ nombre }}» a «{{nombre}}», que es lo que reemplaza el servicio.
        return PATRON.sub(lambda m: "{{%s}}" % m.group(1), texto).strip()

    def clean_asunto(self):
        return self._validar("asunto")

    def clean_cuerpo(self):
        return self._validar("cuerpo")
