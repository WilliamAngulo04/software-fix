from django.contrib import admin

from .models import Venta, VentaDetalle


class VentaDetalleInline(admin.TabularInline):
    model = VentaDetalle
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'fecha_venta', 'cliente', 'orden_servicio', 'metodo_pago', 'total', 'usuario')
    list_filter = ('metodo_pago', 'fecha_venta')
    search_fields = ('cliente__nombre', 'orden_servicio__codigo_orden')
    inlines = [VentaDetalleInline]
