from django.contrib import admin

from .models import DetalleReparacionRepuesto, EvidenciaFotografica, OrdenServicio


class EvidenciaInline(admin.TabularInline):
    model = EvidenciaFotografica
    extra = 0


class RepuestoInline(admin.TabularInline):
    model = DetalleReparacionRepuesto
    extra = 0


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ('codigo_orden', 'equipo', 'estado', 'tecnico', 'fecha_ingreso', 'fecha_promesa', 'costo_final')
    list_filter = ('estado', 'tecnico')
    search_fields = ('codigo_orden', 'equipo__cliente__nombre', 'equipo__numero_serie_imei')
    readonly_fields = ('codigo_orden',)
    inlines = [RepuestoInline, EvidenciaInline]
