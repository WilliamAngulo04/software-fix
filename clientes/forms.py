from django import forms

from config.estilos import BootstrapMixin

from .models import Cliente, Equipo


class ClienteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['documento_id', 'nombre', 'telefono', 'email', 'direccion']

    def clean_documento_id(self):
        # Guardar NULL en vez de '' para no chocar con la restricción UNIQUE.
        return self.cleaned_data['documento_id'] or None


class EquipoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['tipo_dispositivo', 'marca', 'modelo', 'numero_serie_imei', 'clave_patron']
