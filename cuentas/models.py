from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class Establecimiento(models.Model):
    """Taller que usa el sistema. Cada uno ve solo sus propios datos."""

    nombre = models.CharField('nombre del taller', max_length=120)
    nit = models.CharField('NIT / documento', max_length=30, blank=True, null=True)
    telefono = models.CharField('teléfono', max_length=20, blank=True, null=True)
    direccion = models.CharField('dirección', max_length=200, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'establecimientos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


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
        if not extra.get('establecimiento'):
            extra['establecimiento'] = Establecimiento.objects.create(nombre=f'Taller de {nombre}')
        return self.create_user(email, nombre, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Roles del sistema (Administrador, Técnico, Recepcionista)."""

    class Rol(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        TECNICO = 'tecnico', 'Técnico'
        RECEPCION = 'recepcion', 'Recepcionista'

    establecimiento = models.ForeignKey(
        Establecimiento, on_delete=models.PROTECT, related_name='usuarios', null=True, blank=True,
    )
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

    # El panel /admin/ ve los datos de todos los talleres, así que queda reservado al
    # superusuario de la plataforma. Los administradores de cada taller usan la aplicación.
    @property
    def is_staff(self):
        return self.is_superuser

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN

    @property
    def es_tecnico(self):
        return self.rol == self.Rol.TECNICO

    @property
    def es_recepcion(self):
        return self.rol == self.Rol.RECEPCION
