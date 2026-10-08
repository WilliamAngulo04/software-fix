from django.core.exceptions import ValidationError
from django.db import transaction

from inventario.models import ProductoInventario

from .models import DetalleReparacionRepuesto


@transaction.atomic
def agregar_repuesto(orden, producto, cantidad):
    """Registra un repuesto usado en la orden y lo descuenta del inventario."""
    if orden.cerrada:
        raise ValidationError('No se pueden agregar repuestos a una orden cerrada.')
    producto = ProductoInventario.objects.select_for_update().get(pk=producto.pk)
    if cantidad > producto.stock_actual:
        raise ValidationError(
            f'Stock insuficiente de "{producto.nombre}": hay {producto.stock_actual} y se pidieron {cantidad}.'
        )
    producto.stock_actual -= cantidad
    producto.save(update_fields=['stock_actual'])
    return DetalleReparacionRepuesto.objects.create(
        orden=orden, producto=producto, cantidad=cantidad, precio_unitario=producto.precio_venta,
    )


@transaction.atomic
def quitar_repuesto(detalle):
    """Elimina un repuesto de la orden y lo devuelve al inventario."""
    if detalle.orden.cerrada:
        raise ValidationError('No se pueden quitar repuestos de una orden cerrada.')
    producto = ProductoInventario.objects.select_for_update().get(pk=detalle.producto_id)
    producto.stock_actual += detalle.cantidad
    producto.save(update_fields=['stock_actual'])
    detalle.delete()
