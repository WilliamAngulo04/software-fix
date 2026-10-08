from django.contrib import admin

from .models import ProductoInventario


@admin.register(ProductoInventario)
class ProductoInventarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_barras', 'categoria', 'precio_venta', 'stock_actual', 'stock_minimo')
    list_filter = ('categoria', 'es_repuesto')
    search_fields = ('nombre', 'codigo_barras')
