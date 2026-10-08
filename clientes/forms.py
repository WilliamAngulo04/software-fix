from django import forms

from config.estilos import BootstrapMixin

from . import patron
from .models import Cliente, Equipo


class ClienteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['documento_id', 'nombre', 'telefono', 'email', 'direccion']

    def __init__(self, *args, establecimiento, **kwargs):
        super().__init__(*args, **kwargs)
        self.establecimiento = establecimiento

    def clean_documento_id(self):
        # Guardar NULL en vez de '' para no chocar con la restricción UNIQUE.
        documento = self.cleaned_data['documento_id'] or None
        if documento:
            repetido = Cliente.objects.filter(establecimiento=self.establecimiento, documento_id=documento)
            if repetido.exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Ya existe un cliente con este documento.')
        return documento


class EquipoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ['tipo_dispositivo', 'marca', 'modelo', 'numero_serie_imei', 'clave_patron', 'patron']
        widgets = {'patron': patron.PatronInput()}
        help_texts = {
            'clave_patron': 'PIN o contraseña de desbloqueo, si tiene.',
            'patron': 'Si el equipo se desbloquea con patrón, dibújalo aquí.',
        }

    def clean_patron(self):
        return patron.validar(self.cleaned_data.get('patron'))
