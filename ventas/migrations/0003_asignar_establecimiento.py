"""
Paso a multi-establecimiento: los datos que existían antes de este cambio pertenecían a un
único taller, así que se asignan todos a un establecimiento creado para ellos.
"""
from django.db import migrations


def asignar(apps, schema_editor):
    Establecimiento = apps.get_model('cuentas', 'Establecimiento')
    modelos = [
        apps.get_model('cuentas', 'Usuario'),
        apps.get_model('clientes', 'Cliente'),
        apps.get_model('inventario', 'ProductoInventario'),
        apps.get_model('ordenes', 'OrdenServicio'),
        apps.get_model('ventas', 'Venta'),
    ]
    if not any(m.objects.filter(establecimiento__isnull=True).exists() for m in modelos):
        return
    taller = Establecimiento.objects.order_by('id').first() or Establecimiento.objects.create(nombre='Mi taller')
    for modelo in modelos:
        modelo.objects.filter(establecimiento__isnull=True).update(establecimiento=taller)


class Migration(migrations.Migration):
    dependencies = [
        ('cuentas', '0002_establecimiento_usuario_establecimiento'),
        ('clientes', '0002_cliente_establecimiento_alter_cliente_documento_id_and_more'),
        ('inventario', '0002_productoinventario_establecimiento_and_more'),
        ('ordenes', '0002_ordenservicio_establecimiento_and_more'),
        ('ventas', '0002_venta_establecimiento'),
    ]

    operations = [
        migrations.RunPython(asignar, migrations.RunPython.noop),
    ]
