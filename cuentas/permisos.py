from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

ADMIN = 'admin'
TECNICO = 'tecnico'
RECEPCION = 'recepcion'
TODOS = (ADMIN, TECNICO, RECEPCION)


def tiene_rol(usuario, *roles):
    return usuario.is_authenticated and usuario.rol in roles


def exigir_rol(usuario, *roles):
    if not tiene_rol(usuario, *roles):
        raise PermissionDenied('No tienes permiso para realizar esta acción.')


class RolRequeridoMixin(LoginRequiredMixin):
    """Restringe una vista a los roles indicados en `roles`."""

    roles = TODOS

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            exigir_rol(request.user, *self.roles)
        return super().dispatch(request, *args, **kwargs)
