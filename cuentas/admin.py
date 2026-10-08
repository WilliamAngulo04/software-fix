from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Establecimiento, Usuario


@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono', 'creado_en')
    search_fields = ('nombre', 'nit')


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('nombre', 'email', 'establecimiento', 'rol', 'activo', 'creado_en')
    list_filter = ('rol', 'activo', 'establecimiento')
    search_fields = ('nombre', 'email')
    ordering = ('nombre',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos', {'fields': ('establecimiento', 'nombre', 'rol', 'activo')}),
        ('Permisos', {'fields': ('is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('establecimiento', 'email', 'nombre', 'rol', 'password1', 'password2')}),
    )
    filter_horizontal = ('groups', 'user_permissions')
