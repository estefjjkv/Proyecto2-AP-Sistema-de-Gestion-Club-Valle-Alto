from django import forms
from accounts.models import User
from accounts.validators import normalize_id
from .models import MembershipType, Membership, Beneficiary

class TypeForm(forms.ModelForm):
    class Meta:
        model=MembershipType
        fields=("codigo","nombre","cuota","limite_beneficiarios","limite_invitados")
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.instance._state.adding: self.fields["codigo"].disabled=True
    def clean_codigo(self): return self.cleaned_data["codigo"].strip().upper()

class SelectTypeForm(forms.Form):
    tipo=forms.ModelChoiceField(queryset=MembershipType.objects.all())

class MembershipForm(forms.ModelForm):
    motivo=forms.CharField(max_length=300,help_text="Se guardará en el historial cuando cambie el estado.")
    class Meta:
        model=Membership
        fields=("socio","tipo","fecha_inscripcion","fecha_renovacion","cuota","estado")
        widgets={name:forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d") for name in ("fecha_inscripcion","fecha_renovacion")}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.instance._state.adding: self.fields["socio"].disabled=True

class BeneficiaryForm(forms.ModelForm):
    class Meta:
        model=Beneficiary
        fields=("nombre_completo","cedula","parentesco","fecha_nacimiento")
        widgets={"fecha_nacimiento":forms.DateInput(attrs={"type":"date"},format="%Y-%m-%d")}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if not self.instance._state.adding: self.fields["cedula"].disabled=True
    def clean_cedula(self):
        if not self.instance._state.adding: return self.instance.cedula
        return normalize_id(self.cleaned_data["cedula"])
