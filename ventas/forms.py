from django import forms

from clientes.models import Cliente
from config.estilos import BootstrapMixin
from inventario.models import ProductoInventario

from .models import Venta


class VentaForm(BootstrapMixin, forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.all(), required=False, empty_label='Venta de mostrador (sin cliente)',
    )
    metodo_pago = forms.ChoiceField(label='Método de pago', choices=Venta.MetodoPago.choices)

    def __init__(self, *args, orden=None, **kwargs):
        super().__init__(*args, **kwargs)
        if orden is not None:
            # El cliente de una venta de orden es siempre el dueño del equipo.
            del self.fields['cliente']


class LineaVentaForm(BootstrapMixin, forms.Form):
    producto = forms.ModelChoiceField(queryset=ProductoInventario.objects.filter(stock_actual__gt=0))
    cantidad = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].label_from_instance = (
            lambda p: f'{p.nombre} — ${p.precio_venta:,.0f} (stock: {p.stock_actual})'
        )


LineaVentaFormSet = forms.formset_factory(LineaVentaForm, extra=1, can_delete=True)
