from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from inventario.models import ProductoInventario
from ordenes.models import OrdenServicio

from .models import Venta, VentaDetalle


@transaction.atomic
def registrar_venta(usuario, metodo_pago, items, cliente=None, orden=None):
    """
    Crea una venta y descuenta el stock de los productos vendidos.

    items: lista de tuplas (producto, cantidad).
    orden: si se indica, la venta cobra esa orden (suma su costo_final al total)
           y la orden pasa a "entregado".
    """
    if not items and orden is None:
        raise ValidationError('La venta debe tener al menos un producto o una orden de servicio.')

    total = Decimal('0.00')

    if orden is not None:
        orden = OrdenServicio.objects.select_for_update().get(pk=orden.pk)
        if orden.esta_cobrada:
            raise ValidationError(f'La orden {orden} ya fue cobrada.')
        if orden.estado != OrdenServicio.Estado.LISTO_ENTREGA:
            raise ValidationError(f'La orden {orden} debe estar en "Listo para entrega" para cobrarse.')
        cliente = orden.cliente
        total += orden.costo_final

    # Agrupar cantidades por producto y bloquear las filas para evitar sobreventa.
    cantidades = {}
    for producto, cantidad in items:
        cantidades[producto.pk] = cantidades.get(producto.pk, 0) + cantidad
    productos = ProductoInventario.objects.select_for_update().in_bulk(list(cantidades))

    lineas = []
    for pk, cantidad in cantidades.items():
        producto = productos[pk]
        if cantidad > producto.stock_actual:
            raise ValidationError(
                f'Stock insuficiente de "{producto.nombre}": hay {producto.stock_actual} y se pidieron {cantidad}.'
            )
        subtotal = producto.precio_venta * cantidad
        total += subtotal
        lineas.append((producto, cantidad, subtotal))

    venta = Venta.objects.create(
        cliente=cliente, usuario=usuario, orden_servicio=orden, total=total, metodo_pago=metodo_pago,
    )
    for producto, cantidad, subtotal in lineas:
        VentaDetalle.objects.create(
            venta=venta, producto=producto, cantidad=cantidad,
            precio_unitario=producto.precio_venta, subtotal=subtotal,
        )
        producto.stock_actual -= cantidad
        producto.save(update_fields=['stock_actual'])

    if orden is not None:
        orden.estado = OrdenServicio.Estado.ENTREGADO
        orden.save()

    return venta
