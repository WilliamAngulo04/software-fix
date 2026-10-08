from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from clientes.models import Cliente, Equipo
from cuentas.models import Usuario
from inventario.models import ProductoInventario
from ordenes.models import OrdenServicio


class Command(BaseCommand):
    help = 'Carga usuarios, clientes, productos y órdenes de ejemplo para probar el sistema.'

    @transaction.atomic
    def handle(self, *args, **options):
        clave = 'Taller2026*'
        usuarios = {}
        for email, nombre, rol in [
            ('admin@softwarefix.com', 'Administrador', 'admin'),
            ('tecnico@softwarefix.com', 'Carlos Técnico', 'tecnico'),
            ('recepcion@softwarefix.com', 'Laura Recepción', 'recepcion'),
        ]:
            usuario, creado = Usuario.objects.get_or_create(
                email=email, defaults={'nombre': nombre, 'rol': rol, 'is_superuser': rol == 'admin'},
            )
            if creado:
                usuario.set_password(clave)
                usuario.save()
            usuarios[rol] = usuario

        productos = [
            ('7701001', 'Pantalla Samsung A32', 'repuesto', True, 180000, 260000, 4),
            ('7701002', 'Batería iPhone 11', 'repuesto', True, 70000, 120000, 6),
            ('7701003', 'Pin de carga USB-C', 'repuesto', True, 8000, 25000, 15),
            ('7701004', 'Disco SSD 480 GB', 'repuesto', True, 110000, 175000, 1),
            ('7701005', 'Cargador 20W USB-C', 'accesorio', False, 25000, 45000, 10),
            ('7701006', 'Vidrio templado universal', 'accesorio', False, 3000, 15000, 30),
            ('7701007', 'Pasta térmica', 'herramienta', False, 12000, 25000, 2),
        ]
        for codigo, nombre, categoria, es_rep, compra, venta, stock in productos:
            ProductoInventario.objects.get_or_create(codigo_barras=codigo, defaults={
                'nombre': nombre, 'categoria': categoria, 'es_repuesto': es_rep,
                'precio_compra': Decimal(compra), 'precio_venta': Decimal(venta), 'stock_actual': stock,
            })

        ana, _ = Cliente.objects.get_or_create(documento_id='1020304050', defaults={
            'nombre': 'Ana Gómez', 'telefono': '3001234567', 'email': 'ana@example.com',
        })
        luis, _ = Cliente.objects.get_or_create(documento_id='79888777', defaults={
            'nombre': 'Luis Pérez', 'telefono': '3109876543',
        })
        if not ana.equipos.exists():
            celular = Equipo.objects.create(cliente=ana, tipo_dispositivo='celular', marca='Samsung',
                                            modelo='Galaxy A32', numero_serie_imei='356789101112131', clave_patron='1234')
            OrdenServicio.objects.create(
                equipo=celular, recepcionista=usuarios['recepcion'], tecnico=usuarios['tecnico'],
                estado='en_diagnostico', falla_reportada='Pantalla rota, no responde al tacto.',
                observaciones_esteticas='Golpe en la esquina inferior izquierda.', costo_estimado=Decimal(300000),
            )
        if not luis.equipos.exists():
            laptop = Equipo.objects.create(cliente=luis, tipo_dispositivo='laptop', marca='Lenovo',
                                           modelo='IdeaPad 3', numero_serie_imei='PF2XYZ12')
            OrdenServicio.objects.create(
                equipo=laptop, recepcionista=usuarios['recepcion'],
                falla_reportada='Muy lento, se calienta.', costo_estimado=Decimal(220000),
            )

        self.stdout.write(self.style.SUCCESS(
            f'Datos de demostración cargados. Usuarios: admin@, tecnico@, recepcion@softwarefix.com — contraseña: {clave}'
        ))
