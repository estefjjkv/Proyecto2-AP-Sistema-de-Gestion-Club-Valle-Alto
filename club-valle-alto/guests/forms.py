from django import forms
from accounts.validators import normalize_id
from instalaciones.models import Instalacion
from .models import Relation

class GuestForm(forms.Form):
    nombre_completo=forms.CharField(max_length=150,label="Nombre completo")
    cedula=forms.CharField(max_length=20,label="Cédula")
    fecha_visita=forms.DateField(widget=forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d"),label="Fecha de visita")
    instalacion=forms.ModelChoiceField(queryset=Instalacion.objects.filter(activa=True),label="Instalación")
    relacion=forms.ModelChoiceField(queryset=Relation.objects.all(),label="Relación")
    def clean_cedula(self):return normalize_id(self.cleaned_data["cedula"])

class ReceptionFilter(forms.Form):
    fecha=forms.DateField(widget=forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d"))
