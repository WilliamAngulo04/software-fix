from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Sum
from django.utils import timezone

from clientes.models import Equipo
from inventario.models import ProductoInventario


class OrdenServicio(models.Model):
    """Orden principal de servicio técnico."""

    class Estado(models.TextChoices):
        RECIBIDO = 'recibido', 'Recibido'
        EN_DIAGNOSTICO = 'en_diagnostico', 'En diagnóstico'
        ESPERANDO_APROBACION = 'esperando_aprobacion', 'Esperando aprobación'
        EN_REPARACION = 'en_reparacion', 'En reparación'
        LISTO_ENTREGA = 'listo_entrega', 'Listo para entrega'
        ENTREGADO = 'entregado', 'Entregado'
        CANCELADO = 'cancelado', 'Cancelado'

    ESTADOS_CERRADOS = (Estado.ENTREGADO, Estado.CANCELADO)

    codigo_orden = models.CharField('código', max_length=20, unique=True, editable=False)
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='ordenes')
    recepcionista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ordenes_recibidas'
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ordenes_asignadas',
        null=True, blank=True, limit_choices_to={'rol': 'tecnico', 'activo': True},
    )
    estado = models.CharField(max_length=30, choices=Estado.choices, default=Estado.RECIBIDO)

    # Condiciones de ingreso
    falla_reportada = models.TextField()
    diagnostico_tecnico = models.TextField('diagnóstico técnico', blank=True, null=True)
    observaciones_esteticas = models.TextField(
        'observaciones estéticas', blank=True, null=True,
        help_text='Rayones, golpes, falta de tornillos…',
    )

    # Costos y tiempos
    costo_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    costo_final = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    fecha_ingreso = models.DateTimeField(default=timezone.now)
    fecha_promesa = models.DateTimeField('fecha prometida', blank=True, null=True)
    fecha_entrega = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'ordenes_servicio'
        ordering = ['-fecha_ingreso']
        verbose_name = 'orden de servicio'
        verbose_name_plural = 'órdenes de servicio'

    def __str__(self):
        return self.codigo_orden

    def save(self, *args, **kwargs):
        if not self.codigo_orden:
            self.codigo_orden = self.siguiente_codigo()
        if self.estado == self.Estado.ENTREGADO and not self.fecha_entrega:
            self.fecha_entrega = timezone.now()
        super().save(*args, **kwargs)

    @classmethod
    def siguiente_codigo(cls):
        """Genera códigos del tipo ORD-2026-0001, reiniciando el consecutivo cada año."""
        prefijo = f'ORD-{timezone.localdate().year}-'
        ultimo = (
            cls.objects.filter(codigo_orden__startswith=prefijo)
            .order_by('-codigo_orden').values_list('codigo_orden', flat=True).first()
        )
        numero = int(ultimo.rsplit('-', 1)[1]) + 1 if ultimo else 1
        return f'{prefijo}{numero:04d}'

    @property
    def cliente(self):
        return self.equipo.cliente

    @property
    def cerrada(self):
        return self.estado in self.ESTADOS_CERRADOS

    @property
    def total_repuestos(self):
        total = self.repuestos.aggregate(t=Sum(F('cantidad') * F('precio_unitario')))['t']
        return total or Decimal('0.00')

    @property
    def esta_cobrada(self):
        return hasattr(self, 'venta')


class EvidenciaFotografica(models.Model):
    class Momento(models.TextChoices):
        RECEPCION = 'recepcion', 'Recepción'
        PROCESO_TECNICO = 'proceso_tecnico', 'Proceso técnico'
        ENTREGA = 'entrega', 'Entrega'

    orden = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='evidencias')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)  # Quién tomó la foto
    momento = models.CharField(max_length=20, choices=Momento.choices)
    # El archivo se guarda en MEDIA_ROOT; la columna conserva el nombre del esquema (url_foto).
    url_foto = models.ImageField('foto', upload_to='evidencias/%Y/%m/', max_length=500)
    descripcion = models.CharField('descripción', max_length=255, blank=True, null=True)
    tomada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evidencias_fotograficas'
        ordering = ['tomada_en']
        verbose_name = 'evidencia fotográfica'
        verbose_name_plural = 'evidencias fotográficas'

    def __str__(self):
        return f'{self.orden} - {self.get_momento_display()}'


class DetalleReparacionRepuesto(models.Model):
    """Repuestos utilizados específicamente dentro de una orden de servicio."""

    orden = models.ForeignKey(OrdenServicio, on_delete=models.CASCADE, related_name='repuestos')
    producto = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_reparacion_repuestos'
        verbose_name = 'repuesto usado'
        verbose_name_plural = 'repuestos usados'

    def __str__(self):
        return f'{self.cantidad} x {self.producto}'

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
