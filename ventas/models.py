from django.conf import settings
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from inventario.models import ProductoInventario
from ordenes.models import OrdenServicio


class Venta(models.Model):
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA = 'tarjeta', 'Tarjeta'
        TRANSFERENCIA = 'transferencia', 'Transferencia'

    # Puede ser NULL si es venta de mostrador anónima
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True, related_name='compras')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas')
    # Si la venta corresponde al cobro de una orden
    orden_servicio = models.OneToOneField(
        OrdenServicio, on_delete=models.PROTECT, null=True, blank=True, related_name='venta'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField('método de pago', max_length=30, choices=MetodoPago.choices)
    fecha_venta = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ventas'
        ordering = ['-fecha_venta']

    def __str__(self):
        return f'Venta #{self.pk}'


class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(ProductoInventario, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'venta_detalles'

    def __str__(self):
        return f'{self.cantidad} x {self.producto}'
