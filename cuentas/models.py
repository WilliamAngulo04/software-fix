from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, password=None, **extra):
        if not email:
            raise ValueError('El usuario debe tener un email')
        usuario = self.model(email=self.normalize_email(email), nombre=nombre, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, nombre, password=None, **extra):
        extra.setdefault('rol', Usuario.Rol.ADMIN)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Roles del sistema (Administrador, Técnico, Recepcionista)."""

    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        TECNICO = 'tecnico', 'Técnico'
        RECEPCION = 'recepcion', 'Recepcionista'

    nombre = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    rol = models.CharField(max_length=20, choices=Rol.choices)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    # AbstractBaseUser guarda la contraseña en "password"; la mapeamos a password_hash.
    password = models.CharField('contraseña', max_length=255, db_column='password_hash')

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuarios'
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rol__in=['admin', 'tecnico', 'recepcion']),
                name='usuarios_rol_valido',
            ),
        ]

    def __str__(self):
        return self.nombre

    # Django usa is_active / is_staff; los derivamos de las columnas del esquema.
    @property
    def is_active(self):
        return self.activo

    @property
    def is_staff(self):
        return self.rol == self.Rol.ADMIN

    # Un administrador activo tiene todos los permisos (incluido el panel /admin).
    def has_perm(self, perm, obj=None):
        if self.activo and self.es_admin:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.activo and self.es_admin:
            return True
        return super().has_module_perms(app_label)

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN

    @property
    def es_tecnico(self):
        return self.rol == self.Rol.TECNICO

    @property
    def es_recepcion(self):
        return self.rol == self.Rol.RECEPCION
