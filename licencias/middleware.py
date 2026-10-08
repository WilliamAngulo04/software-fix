from django.shortcuts import redirect
from django.urls import reverse

# Rutas que siguen disponibles con la licencia vencida.
RUTAS_LIBRES = ('/licencia/', '/planes/', '/consulta/', '/login/', '/logout/', '/registro/', '/admin/', '/static/', '/media/')


class LicenciaMiddleware:
    """Bloquea el uso de la aplicación a los talleres con la licencia vencida."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if (
            usuario.is_authenticated
            and not usuario.is_superuser
            and usuario.establecimiento_id
            and not request.path.startswith(RUTAS_LIBRES)
            and not usuario.establecimiento.licencia_vigente
        ):
            return redirect(reverse('mi_licencia'))
        return self.get_response(request)
