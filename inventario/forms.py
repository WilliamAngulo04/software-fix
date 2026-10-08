from django import forms

from config.estilos import BootstrapMixin

from .models import ProductoInventario


class ProductoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ProductoInventario
        fields = [
            'codigo_barras', 'nombre', 'categoria', 'es_repuesto',
            'precio_compra', 'precio_venta', 'stock_actual', 'stock_minimo',
        ]

    def __init__(self, *args, establecimiento, **kwargs):
        super().__init__(*args, **kwargs)
        self.establecimiento = establecimiento

    def clean_codigo_barras(self):
        codigo = self.cleaned_data['codigo_barras'] or None
        if codigo:
            repetido = ProductoInventario.objects.filter(establecimiento=self.establecimiento, codigo_barras=codigo)
            if repetido.exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Ya existe un producto con este código de barras.')
        return codigo

    def clean(self):
        datos = super().clean()
        for campo in ('precio_compra', 'precio_venta', 'stock_actual', 'stock_minimo'):
            if datos.get(campo) is not None and datos[campo] < 0:
                self.add_error(campo, 'No puede ser negativo.')
        return datos
