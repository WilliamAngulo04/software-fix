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
    """
    Restringe una vista a los roles indicados en `roles` y expone el taller del usuario
    en `self.establecimiento`.

    Si la vista define `campo_establecimiento`, get_queryset() se limita a los registros
    de ese taller, de modo que los objetos de otros talleres responden 404.
    """

    roles = TODOS
    campo_establecimiento = None

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            exigir_rol(request.user, *self.roles)
            if request.user.establecimiento_id is None:
                raise PermissionDenied('Tu usuario no pertenece a ningún establecimiento.')
            self.establecimiento = request.user.establecimiento
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.campo_establecimiento:
            qs = qs.filter(**{self.campo_establecimiento: self.establecimiento})
        return qs
