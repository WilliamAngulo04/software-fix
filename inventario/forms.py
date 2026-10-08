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

    def clean_codigo_barras(self):
        return self.cleaned_data['codigo_barras'] or None

    def clean(self):
        datos = super().clean()
        for campo in ('precio_compra', 'precio_venta', 'stock_actual', 'stock_minimo'):
            if datos.get(campo) is not None and datos[campo] < 0:
                self.add_error(campo, 'No puede ser negativo.')
        return datos
