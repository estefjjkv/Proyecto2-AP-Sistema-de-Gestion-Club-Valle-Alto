from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm
from .models import User, Administrator
from .validators import normalize_id, normalize_phone


class PersonalDataMixin:
    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = self._meta.model.objects.filter(email__iexact=email)
        if not self.instance._state.adding: qs = qs.exclude(pk=self.instance.pk)
        if qs.exists(): raise forms.ValidationError("Ya existe una cuenta de este tipo con ese correo.")
        return email
    def clean_cedula(self):
        if not self.instance._state.adding: return self.instance.cedula
        return normalize_id(self.cleaned_data["cedula"])
    def clean_telefono(self): return normalize_phone(self.cleaned_data["telefono"])


class PasswordFormMixin:
    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        if data.get("password1"):
            candidate = self._meta.model(email=data.get("email", ""), nombre_completo=data.get("nombre_completo", ""))
            try: password_validation.validate_password(data["password1"], candidate)
            except forms.ValidationError as error: self.add_error("password1", error)
        return data
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit: user.save(force_insert=True)
        return user


class RegistroSocioForm(PasswordFormMixin, PersonalDataMixin, forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ("nombre_completo", "cedula", "email", "telefono", "direccion", "fecha_nacimiento")
        widgets = {"fecha_nacimiento": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"), "direccion": forms.Textarea(attrs={"rows":2})}


class PerfilForm(PersonalDataMixin, forms.ModelForm):
    class Meta(RegistroSocioForm.Meta): pass
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # PK referenciada por reservas, cargos y membresía: no editar como un dato común.
        self.fields["cedula"].disabled = True
        self.fields["cedula"].help_text = "La cédula identifica su cuenta y no se modifica desde el perfil."


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico")
    cuenta = forms.ChoiceField(label="Tipo de cuenta", choices=[("socio", "Socio"), ("administrador", "Personal administrativo")])
    def clean(self):
        username, password = self.cleaned_data.get("username"), self.cleaned_data.get("password")
        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password, cuenta=self.cleaned_data.get("cuenta", "socio"))
            if self.user_cache is None:
                raise forms.ValidationError("No fue posible iniciar sesión. Revise tipo de cuenta, correo y contraseña. Tras 5 intentos fallidos espere 15 minutos; las cuentas inactivas no pueden ingresar.")
        return self.cleaned_data


class AdminCreateForm(PasswordFormMixin, PersonalDataMixin, forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)
    class Meta:
        model = Administrator
        fields = ("nombre_completo", "cedula", "email", "rol")


class AdminEditForm(PersonalDataMixin, forms.ModelForm):
    class Meta:
        model = Administrator
        fields = ("nombre_completo", "cedula", "email", "rol", "activo")
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["cedula"].disabled=True


class RecoveryRequestForm(forms.Form):
    email = forms.EmailField(label="Correo electrónico del socio", max_length=150)
