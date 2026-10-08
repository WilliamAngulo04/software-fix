from django.conf import settings
from django.db import models

from cuentas.models import Establecimiento


class PlanLicencia(models.Model):
    """Planes que puede comprar un taller (mensual, trimestral, semestral, anual)."""

    nombre = models.CharField(max_length=50)
    dias = models.PositiveIntegerField('días de duración')
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField('descripción', max_length=200, blank=True)
    activo = models.BooleanField('disponible para la venta', default=True)
    orden = models.PositiveSmallIntegerField(default=0, help_text='Posición en la página de planes.')

    class Meta:
        db_table = 'planes_licencia'
        ordering = ['orden', 'dias']
        verbose_name = 'plan de licencia'
        verbose_name_plural = 'planes de licencia'

    def __str__(self):
        return f'{self.nombre} ({self.dias} días)'

    @property
    def precio_mensual(self):
        """Precio equivalente por mes, para mostrar el ahorro de los planes largos."""
        return self.precio * 30 / max(self.dias, 30)


class Licencia(models.Model):
    """Compra de un plan por un taller: primero es una solicitud y el superusuario la aprueba."""

    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente de aprobación'
        APROBADA = 'aprobada', 'Aprobada'
        RECHAZADA = 'rechazada', 'Rechazada'

    establecimiento = models.ForeignKey(Establecimiento, on_delete=models.CASCADE, related_name='licencias')
    plan = models.ForeignKey(PlanLicencia, on_delete=models.PROTECT, related_name='licencias')
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True,
        help_text='Precio del plan al momento de la compra. Vacío = precio actual del plan.',
    )
    referencia_pago = models.CharField(
        'referencia de pago', max_length=100, blank=True,
        help_text='Número de comprobante, transferencia o Nequi que indicó el taller.',
    )
    notas = models.TextField('notas internas', blank=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True, editable=False)
    fecha_fin = models.DateTimeField(null=True, blank=True, editable=False)
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='licencias_solicitadas', editable=False,
    )
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='licencias_aprobadas', editable=False,
    )
    creado_en = models.DateTimeField('solicitada el', auto_now_add=True)
    aprobada_en = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        db_table = 'licencias'
        ordering = ['-creado_en']

    def __str__(self):
        return f'{self.establecimiento} — {self.plan.nombre} ({self.get_estado_display()})'


class ConfiguracionPlataforma(models.Model):
    """Ajustes generales que administra el superusuario (un único registro)."""

    dias_prueba = models.PositiveIntegerField('días de prueba gratis', default=7)
    instrucciones_pago = models.TextField(
        'instrucciones de pago',
        default='Realiza el pago por transferencia o Nequi y escribe la referencia del comprobante '
                'en tu solicitud. La licencia se activa en cuanto confirmemos el pago.',
    )
    whatsapp = models.CharField('WhatsApp de contacto', max_length=20, blank=True, help_text='Ej: 573001234567')
    email_contacto = models.EmailField('email de contacto', blank=True)

    class Meta:
        db_table = 'configuracion_plataforma'
        verbose_name = 'configuración de la plataforma'
        verbose_name_plural = 'configuración de la plataforma'

    def __str__(self):
        return 'Configuración de la plataforma'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        return cls.objects.get_or_create(pk=1)[0]
