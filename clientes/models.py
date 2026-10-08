from django.db import models

from cuentas.models import Establecimiento


class Cliente(models.Model):
    """Datos del cliente."""

    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.CASCADE, related_name='clientes')
    documento_id = models.CharField('documento', max_length=20, null=True, blank=True)
    nombre = models.CharField(max_length=100)
    telefono = models.CharField('teléfono', max_length=20)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.TextField('dirección', blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clientes'
        ordering = ['nombre']
        constraints = [
            models.UniqueConstraint(fields=['establecimiento', 'documento_id'], name='clientes_documento_unico'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.documento_id})' if self.documento_id else self.nombre


class Equipo(models.Model):
    """Dispositivos pertenecientes a los clientes."""

    class TipoDispositivo(models.TextChoices):
        CELULAR = 'celular', 'Celular'
        LAPTOP = 'laptop', 'Laptop'
        PC_ESCRITORIO = 'pc_escritorio', 'PC de escritorio'
        TABLET = 'tablet', 'Tablet'

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='equipos')
    tipo_dispositivo = models.CharField('tipo', max_length=30, choices=TipoDispositivo.choices)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    numero_serie_imei = models.CharField('serie / IMEI', max_length=50, blank=True, null=True)
    clave_patron = models.CharField('clave o patrón', max_length=100, blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'equipos'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.get_tipo_dispositivo_display()} {self.marca} {self.modelo}'
