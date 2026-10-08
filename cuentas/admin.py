from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('nombre', 'email', 'rol', 'activo', 'creado_en')
    list_filter = ('rol', 'activo')
    search_fields = ('nombre', 'email')
    ordering = ('nombre',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos', {'fields': ('nombre', 'rol', 'activo')}),
        ('Permisos', {'fields': ('is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'nombre', 'rol', 'password1', 'password2')}),
    )
    filter_horizontal = ('groups', 'user_permissions')
