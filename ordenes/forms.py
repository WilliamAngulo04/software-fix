from django import forms

from clientes.models import Equipo
from config.estilos import BootstrapMixin, FechaHoraInput
from cuentas.models import Usuario
from inventario.models import ProductoInventario

from .models import EvidenciaFotografica, OrdenServicio


def tecnicos_activos():
    return Usuario.objects.filter(rol=Usuario.Rol.TECNICO, activo=True)


class OrdenForm(BootstrapMixin, forms.ModelForm):
    """Recepción de un equipo: crea la orden."""

    class Meta:
        model = OrdenServicio
        fields = [
            'equipo', 'tecnico', 'falla_reportada', 'observaciones_esteticas',
            'costo_estimado', 'fecha_promesa',
        ]
        widgets = {'fecha_promesa': FechaHoraInput()}

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        equipos = Equipo.objects.select_related('cliente')
        if cliente is not None:
            equipos = equipos.filter(cliente=cliente)
        self.fields['equipo'].queryset = equipos
        self.fields['equipo'].label_from_instance = lambda e: f'{e.cliente.nombre} — {e}'
        self.fields['tecnico'].queryset = tecnicos_activos()


class OrdenGestionForm(BootstrapMixin, forms.ModelForm):
    """Actualización del trabajo técnico: estado, diagnóstico, costos y fechas."""

    class Meta:
        model = OrdenServicio
        fields = [
            'estado', 'tecnico', 'diagnostico_tecnico', 'observaciones_esteticas',
            'costo_estimado', 'costo_final', 'fecha_promesa',
        ]
        widgets = {'fecha_promesa': FechaHoraInput()}

    def __init__(self, *args, puede_asignar=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = tecnicos_activos()
        # "Entregado" solo se alcanza al cobrar la orden en Ventas.
        self.fields['estado'].choices = [
            c for c in OrdenServicio.Estado.choices
            if c[0] != OrdenServicio.Estado.ENTREGADO or self.instance.estado == c[0]
        ]
        if not puede_asignar:
            del self.fields['tecnico']

    def clean(self):
        datos = super().clean()
        for campo in ('costo_estimado', 'costo_final'):
            if datos.get(campo) is not None and datos[campo] < 0:
                self.add_error(campo, 'No puede ser negativo.')
        return datos


class EvidenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = EvidenciaFotografica
        fields = ['momento', 'url_foto', 'descripcion']
        widgets = {'url_foto': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'})}


class RepuestoForm(BootstrapMixin, forms.Form):
    producto = forms.ModelChoiceField(
        queryset=ProductoInventario.objects.filter(stock_actual__gt=0).order_by('-es_repuesto', 'nombre'),
    )
    cantidad = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].label_from_instance = (
            lambda p: f'{p.nombre} — ${p.precio_venta:,.0f} (stock: {p.stock_actual})'
        )
