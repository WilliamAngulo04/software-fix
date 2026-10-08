from django.contrib import admin

from .models import Cliente, Equipo


class EquipoInline(admin.TabularInline):
    model = Equipo
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'documento_id', 'telefono', 'email', 'creado_en')
    list_filter = ('establecimiento',)
    search_fields = ('nombre', 'documento_id', 'telefono', 'email')
    inlines = [EquipoInline]


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'cliente', 'numero_serie_imei', 'creado_en')
    list_filter = ('tipo_dispositivo', 'marca')
    search_fields = ('marca', 'modelo', 'numero_serie_imei', 'cliente__nombre')
    autocomplete_fields = ('cliente',)
