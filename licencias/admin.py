from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone

from cuentas.admin import EstablecimientoAdmin
from cuentas.models import Establecimiento

from . import services
from .models import ConfiguracionPlataforma, Licencia, PlanLicencia


@admin.register(PlanLicencia)
class PlanLicenciaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'dias', 'precio', 'activo', 'orden')
    list_editable = ('precio', 'activo', 'orden')


@admin.register(Licencia)
class LicenciaAdmin(admin.ModelAdmin):
    list_display = (
        'establecimiento', 'plan', 'estado', 'valor', 'referencia_pago', 'creado_en', 'fecha_inicio', 'fecha_fin',
    )
    list_filter = ('estado', 'plan')
    search_fields = ('establecimiento__nombre', 'referencia_pago')
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'solicitada_por', 'aprobada_por', 'aprobada_en', 'creado_en')
    autocomplete_fields = ('establecimiento',)
    actions = ['aprobar_seleccionadas', 'rechazar_seleccionadas']

    def get_changeform_initial_data(self, request):
        return {**super().get_changeform_initial_data(request), 'estado': Licencia.Estado.APROBADA}

    def get_readonly_fields(self, request, obj=None):
        # Una licencia ya aprobada no se modifica (cambiaría las fechas del taller); se crea otra.
        if obj and obj.estado == Licencia.Estado.APROBADA:
            return [*self.readonly_fields, 'establecimiento', 'plan', 'estado', 'valor']
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if obj.valor is None:
            obj.valor = obj.plan.precio
        quiere_aprobar = obj.estado == Licencia.Estado.APROBADA and obj.fecha_fin is None
        if quiere_aprobar:
            obj.estado = Licencia.Estado.PENDIENTE
        super().save_model(request, obj, form, change)
        if quiere_aprobar:
            services.aprobar(obj, request.user)
            obj.refresh_from_db()
            messages.success(request, f'{obj.establecimiento}: licencia activa hasta {obj.fecha_fin:%d/%m/%Y}.')

    @admin.action(description='Aprobar y activar las licencias seleccionadas')
    def aprobar_seleccionadas(self, request, queryset):
        for licencia in queryset.filter(estado=Licencia.Estado.PENDIENTE):
            licencia = services.aprobar(licencia, request.user)
            self.message_user(request, f'{licencia.establecimiento}: activa hasta {licencia.fecha_fin:%d/%m/%Y}.')

    @admin.action(description='Rechazar las solicitudes seleccionadas')
    def rechazar_seleccionadas(self, request, queryset):
        for licencia in queryset:
            try:
                services.rechazar(licencia, request.user)
            except ValidationError as error:
                self.message_user(request, f'{licencia}: {error.messages[0]}', messages.WARNING)


class VigenciaFilter(admin.SimpleListFilter):
    title = 'licencia'
    parameter_name = 'licencia'

    def lookups(self, request, model_admin):
        return [('vigente', 'Vigente'), ('vencida', 'Vencida')]

    def queryset(self, request, queryset):
        ahora = timezone.now()
        if self.value() == 'vigente':
            return queryset.filter(licencia_hasta__gt=ahora)
        if self.value() == 'vencida':
            return queryset.exclude(licencia_hasta__gt=ahora)
        return queryset


class LicenciaInline(admin.TabularInline):
    model = Licencia
    extra = 0
    can_delete = False
    fields = ('plan', 'estado', 'valor', 'referencia_pago', 'fecha_inicio', 'fecha_fin', 'creado_en')
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ConfiguracionPlataforma)
class ConfiguracionPlataformaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracionPlataforma.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# El superusuario ve y ajusta la licencia de cada taller desde su ficha.
admin.site.unregister(Establecimiento)


@admin.register(Establecimiento)
class EstablecimientoLicenciaAdmin(EstablecimientoAdmin):
    list_display = ('nombre', 'nit', 'telefono', 'licencia_hasta', 'estado_licencia', 'creado_en')
    list_filter = (VigenciaFilter,)
    fields = ('nombre', 'nit', 'telefono', 'direccion', 'licencia_hasta')
    inlines = [LicenciaInline]

    @admin.display(description='Estado')
    def estado_licencia(self, obj):
        if not obj.licencia_vigente:
            return '❌ Vencida'
        return f'✅ {obj.dias_restantes} días' + (' (prueba)' if obj.en_prueba else '')
