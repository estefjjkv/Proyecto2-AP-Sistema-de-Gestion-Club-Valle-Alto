from django import forms
from django.db.models import Q
from django.utils import timezone

from instalaciones.models import Instalacion, ServicioAdicional
from socios.models import Socio


class OpcionesConTipo:
    """Agrega data-tipo (y data-aforo para instalaciones) a cada opción, para el filtrado en el navegador."""
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        opcion = super().create_option(name, value, label, selected, index, subindex, attrs)
        objeto = getattr(value, "instance", None)
        if isinstance(objeto, Instalacion):
            opcion["attrs"].update({"data-tipo": objeto.tipo_id, "data-aforo": objeto.aforo_maximo})
        elif isinstance(objeto, ServicioAdicional):
            opcion["attrs"]["data-tipo"] = objeto.tipo_instalacion_id
        return opcion


class SelectInstalacion(OpcionesConTipo, forms.Select):
    pass


class CasillasServicios(OpcionesConTipo, forms.CheckboxSelectMultiple):
    pass


class ServicioChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, servicio):
        return f"{servicio.nombre} (₡{servicio.precio:,.0f})".replace(",", " ")


class ReservaForm(forms.Form):
    instalacion = forms.ModelChoiceField(queryset=Instalacion.objects.none(), label="Instalación", widget=SelectInstalacion)
    fecha = forms.DateField(label="Fecha", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hora_inicio = forms.TimeField(label="Hora de inicio", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M"))
    hora_fin = forms.TimeField(label="Hora de finalización", widget=forms.TimeInput(attrs={"type": "time", "step": 900}, format="%H:%M"))
    numero_personas = forms.IntegerField(label="Número de personas", min_value=1)
    servicios = ServicioChoiceField(queryset=ServicioAdicional.objects.none(), required=False,
                                    label="Servicios adicionales", widget=CasillasServicios)

    def __init__(self, *args, reserva=None, **kwargs):
        if reserva is not None:
            kwargs.setdefault("initial", {}).update({
                "instalacion": reserva.instalacion_id, "fecha": reserva.fecha, "hora_inicio": reserva.hora_inicio,
                "hora_fin": reserva.hora_fin, "numero_personas": reserva.numero_personas,
                "servicios": list(reserva.servicios.values_list("servicio_id", flat=True)),
            })
        super().__init__(*args, **kwargs)
        # Además de lo disponible, se conserva lo que la reserva ya tenía aunque se haya desactivado.
        actual = Q(pk=reserva.instalacion_id) if reserva else Q(pk__in=[])
        actuales = Q(pk__in=reserva.servicios.values("servicio_id")) if reserva else Q(pk__in=[])
        self.fields["instalacion"].queryset = Instalacion.objects.filter(Q(activa=True) | actual).order_by("nombre")
        self.fields["servicios"].queryset = ServicioAdicional.objects.filter(Q(activo=True) | actuales).order_by("nombre")
        self.fields["fecha"].widget.attrs["min"] = timezone.localdate().isoformat()

    def clean(self):
        data = super().clean()
        instalacion = data.get("instalacion")
        if instalacion:
            # Las casillas de otros tipos se ocultan en el navegador; aquí se ignoran por si acaso.
            data["servicios"] = [s for s in data.get("servicios", []) if s.tipo_instalacion_id == instalacion.tipo_id]
        inicio, fin = data.get("hora_inicio"), data.get("hora_fin")
        if inicio and fin and fin <= inicio:
            self.add_error("hora_fin", "Debe ser posterior a la hora de inicio.")
        return data


class SocioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, socio):
        return f"{socio.nombre_completo} · {socio.cedula}"


class AdminReservaForm(ReservaForm):
    """Para administración: al crear se elige el socio titular."""
    socio = SocioChoiceField(queryset=Socio.objects.filter(estado_id="ACTIVA").order_by("nombre_completo"),
                             label="Socio titular")
    field_order = ["socio", "instalacion", "fecha", "hora_inicio", "hora_fin", "numero_personas", "servicios"]

    def __init__(self, *args, reserva=None, **kwargs):
        super().__init__(*args, reserva=reserva, **kwargs)
        if reserva is not None:
            del self.fields["socio"]
