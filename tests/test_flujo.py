import io
import shutil
import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from clientes.models import Cliente, Equipo
from cuentas.models import Establecimiento, Usuario
from inventario.models import ProductoInventario
from ordenes import services as orden_services
from ordenes.models import OrdenServicio
from ventas import services as venta_services

MEDIA_TMP = tempfile.mkdtemp()



def imagen_png():
    """Genera un PNG válido de 1x1 píxel."""
    archivo = io.BytesIO()
    Image.new('RGB', (1, 1)).save(archivo, 'PNG')
    return archivo.getvalue()


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class Base(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TMP, ignore_errors=True)

    def setUp(self):
        self.taller = t = Establecimiento.objects.create(nombre='Taller Uno')
        self.admin = Usuario.objects.create_user(
            'a@x.com', 'Admin', 'clave-segura-1', rol='admin', establecimiento=t,
        )
        self.tecnico = Usuario.objects.create_user(
            't@x.com', 'Tec', 'clave-segura-1', rol='tecnico', establecimiento=t,
        )
        self.otro_tecnico = Usuario.objects.create_user(
            't2@x.com', 'Tec2', 'clave-segura-1', rol='tecnico', establecimiento=t,
        )
        self.recepcion = Usuario.objects.create_user(
            'r@x.com', 'Rec', 'clave-segura-1', rol='recepcion', establecimiento=t,
        )
        self.cliente = Cliente.objects.create(establecimiento=t, nombre='Ana', telefono='300', documento_id='123')
        self.equipo = Equipo.objects.create(
            cliente=self.cliente, tipo_dispositivo='celular', marca='Samsung', modelo='A32',
        )
        self.pantalla = ProductoInventario.objects.create(
            establecimiento=t, nombre='Pantalla', categoria='repuesto', precio_compra=100, precio_venta=200,
            stock_actual=3, es_repuesto=True,
        )
        self.cargador = ProductoInventario.objects.create(
            establecimiento=t, nombre='Cargador', categoria='accesorio', precio_compra=20, precio_venta=50,
            stock_actual=10,
        )
        self.orden = OrdenServicio.objects.create(
            establecimiento=t, equipo=self.equipo, recepcionista=self.recepcion, tecnico=self.tecnico,
            falla_reportada='No enciende',
        )


class OrdenTests(Base):
    def test_codigo_consecutivo(self):
        segunda = OrdenServicio.objects.create(
            establecimiento=self.taller, equipo=self.equipo, recepcionista=self.recepcion, falla_reportada='x',
        )
        self.assertRegex(self.orden.codigo_orden, r'^ORD-\d{4}-0001$')
        self.assertTrue(segunda.codigo_orden.endswith('-0002'))

    def test_repuesto_descuenta_y_devuelve_stock(self):
        detalle = orden_services.agregar_repuesto(self.orden, self.pantalla, 2)
        self.pantalla.refresh_from_db()
        self.assertEqual(self.pantalla.stock_actual, 1)
        self.assertEqual(self.orden.total_repuestos, Decimal('400'))
        orden_services.quitar_repuesto(detalle)
        self.pantalla.refresh_from_db()
        self.assertEqual(self.pantalla.stock_actual, 3)

    def test_repuesto_sin_stock(self):
        with self.assertRaises(ValidationError):
            orden_services.agregar_repuesto(self.orden, self.pantalla, 5)
        self.pantalla.refresh_from_db()
        self.assertEqual(self.pantalla.stock_actual, 3)


class VentaTests(Base):
    def test_venta_mostrador(self):
        venta = venta_services.registrar_venta(
            self.recepcion, 'efectivo', [(self.cargador, 2), (self.cargador, 1)],
        )
        self.assertEqual(venta.total, Decimal('150'))
        self.assertIsNone(venta.cliente)
        self.assertEqual(venta.detalles.get().cantidad, 3)
        self.cargador.refresh_from_db()
        self.assertEqual(self.cargador.stock_actual, 7)

    def test_venta_sin_stock_no_cambia_nada(self):
        with self.assertRaises(ValidationError):
            venta_services.registrar_venta(
                self.recepcion, 'efectivo', [(self.cargador, 1), (self.pantalla, 9)],
            )
        self.cargador.refresh_from_db()
        self.assertEqual(self.cargador.stock_actual, 10)

    def test_cobrar_orden(self):
        self.orden.estado = 'listo_entrega'
        self.orden.costo_final = Decimal('300')
        self.orden.save()
        venta = venta_services.registrar_venta(
            self.recepcion, 'tarjeta', [(self.cargador, 1)], orden=self.orden,
        )
        self.assertEqual(venta.total, Decimal('350'))
        self.assertEqual(venta.cliente, self.cliente)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, 'entregado')
        self.assertIsNotNone(self.orden.fecha_entrega)
        with self.assertRaises(ValidationError):
            venta_services.registrar_venta(self.recepcion, 'efectivo', [], orden=self.orden)

    def test_no_cobra_orden_no_lista(self):
        with self.assertRaises(ValidationError):
            venta_services.registrar_venta(self.recepcion, 'efectivo', [], orden=self.orden)


class VistasTests(Base):
    def entrar(self, usuario):
        self.client.force_login(usuario)

    def test_login_por_email(self):
        r = self.client.post(reverse('login'), {'username': 'a@x.com', 'password': 'clave-segura-1'})
        self.assertRedirects(r, reverse('dashboard'))

    def test_usuario_inactivo_no_entra(self):
        self.admin.activo = False
        self.admin.save()
        r = self.client.post(reverse('login'), {'username': 'a@x.com', 'password': 'clave-segura-1'})
        self.assertEqual(r.status_code, 200)

    def test_paginas_cargan_para_cada_rol(self):
        venta = venta_services.registrar_venta(self.recepcion, 'efectivo', [(self.cargador, 1)])
        comunes = [
            reverse('dashboard'), reverse('orden_list'), reverse('orden_list') + '?estado=abiertas&q=ana',
            reverse('orden_detail', args=[self.orden.pk]), reverse('orden_comprobante', args=[self.orden.pk]),
            reverse('cliente_list') + '?q=an', reverse('cliente_detail', args=[self.cliente.pk]),
            reverse('producto_list') + '?stock_bajo=1',
        ]
        caja = [
            reverse('venta_list'), reverse('venta_detail', args=[venta.pk]), reverse('venta_create'),
            reverse('orden_create'), reverse('cliente_create'), reverse('equipo_create', args=[self.cliente.pk]),
        ]
        solo_admin = [reverse('usuario_list'), reverse('usuario_create'), reverse('producto_create')]

        for usuario, permitidas, prohibidas in [
            (self.admin, comunes + caja + solo_admin + [reverse('establecimiento_update')], []),
            (self.recepcion, comunes + caja, solo_admin),
            (self.tecnico, comunes, caja + solo_admin),
        ]:
            self.entrar(usuario)
            for url in permitidas:
                with self.subTest(rol=usuario.rol, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)
            for url in prohibidas:
                with self.subTest(rol=usuario.rol, url=url, esperado=403):
                    self.assertEqual(self.client.get(url).status_code, 403)

    def test_recepcion_con_cliente_y_equipo_registrados(self):
        self.entrar(self.recepcion)
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk,
            'modo_equipo': 'existente', 'equipo': self.equipo.pk,
            'falla_reportada': 'Pantalla rota', 'costo_estimado': '100',
        })
        nueva = OrdenServicio.objects.latest('id')
        self.assertRedirects(r, reverse('orden_detail', args=[nueva.pk]))
        self.assertEqual(nueva.recepcionista, self.recepcion)
        self.assertEqual(nueva.equipo, self.equipo)

    def test_recepcion_con_cliente_y_equipo_nuevos(self):
        self.entrar(self.recepcion)
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'nuevo', 'cli-nombre': 'Pedro', 'cli-telefono': '311', 'cli-documento_id': '999',
            # Aunque llegue "existente", un cliente nuevo siempre registra equipo nuevo.
            'modo_equipo': 'existente',
            'eq-tipo_dispositivo': 'tablet', 'eq-marca': 'Apple', 'eq-modelo': 'iPad 9', 'eq-clave_patron': '0000',
            'tecnico': self.tecnico.pk, 'falla_reportada': 'No carga', 'costo_estimado': '50000',
        })
        nueva = OrdenServicio.objects.latest('id')
        self.assertRedirects(r, reverse('orden_detail', args=[nueva.pk]))
        self.assertEqual(nueva.cliente.nombre, 'Pedro')
        self.assertEqual(nueva.cliente.establecimiento, self.taller)
        self.assertEqual(str(nueva.equipo), 'Tablet Apple iPad 9')
        self.assertEqual(nueva.tecnico, self.tecnico)

    def test_recepcion_equipo_nuevo_para_cliente_registrado(self):
        self.entrar(self.recepcion)
        self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk, 'modo_equipo': 'nuevo',
            'eq-tipo_dispositivo': 'laptop', 'eq-marca': 'Dell', 'eq-modelo': 'XPS',
            'falla_reportada': 'Teclado', 'costo_estimado': '0',
        })
        self.assertEqual(self.cliente.equipos.count(), 2)

    def test_recepcion_con_errores_no_guarda_nada(self):
        self.entrar(self.recepcion)
        # Documento repetido, equipo de otro cliente y falta la falla.
        otro = Cliente.objects.create(establecimiento=self.taller, nombre='Otro', telefono='1')
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'nuevo', 'cli-nombre': 'X', 'cli-telefono': '1', 'cli-documento_id': '123',
            'eq-tipo_dispositivo': 'celular', 'eq-marca': 'A', 'eq-modelo': 'B', 'costo_estimado': '0',
        })
        self.assertContains(r, 'Ya existe un cliente con este documento')
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': otro.pk, 'modo_equipo': 'existente', 'equipo': self.equipo.pk,
            'falla_reportada': 'x', 'costo_estimado': '0',
        })
        self.assertContains(r, 'Ese equipo no pertenece al cliente seleccionado')
        self.assertEqual(OrdenServicio.objects.count(), 1)
        self.assertEqual(Cliente.objects.count(), 2)

    def datos_recepcion(self, **extra):
        return {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk,
            'modo_equipo': 'existente', 'equipo': self.equipo.pk,
            'falla_reportada': 'Pantalla rota', 'costo_estimado': '0', **extra,
        }

    def test_recepcion_con_fotos(self):
        self.entrar(self.recepcion)
        fotos = [SimpleUploadedFile(f'f{i}.png', imagen_png(), content_type='image/png') for i in range(3)]
        r = self.client.post(reverse('orden_create'), self.datos_recepcion(fotos=fotos, descripcion_fotos='Rayón'))
        nueva = OrdenServicio.objects.latest('id')
        self.assertRedirects(r, reverse('orden_detail', args=[nueva.pk]), fetch_redirect_response=False)
        self.assertEqual(nueva.evidencias.count(), 3)
        evidencia = nueva.evidencias.first()
        self.assertEqual((evidencia.momento, evidencia.descripcion, evidencia.usuario),
                         ('recepcion', 'Rayón', self.recepcion))
        self.assertContains(self.client.get(r.url), 'con 3 fotos')

    def test_recepcion_rechaza_fotos_invalidas_sin_guardar_nada(self):
        self.entrar(self.recepcion)
        antes = OrdenServicio.objects.count()
        falsa = SimpleUploadedFile('virus.png', b'esto no es una imagen', content_type='image/png')
        r = self.client.post(reverse('orden_create'), self.datos_recepcion(fotos=[falsa]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'vuelve a elegirlas')
        demasiadas = [SimpleUploadedFile(f'f{i}.png', imagen_png(), content_type='image/png') for i in range(9)]
        r = self.client.post(reverse('orden_create'), self.datos_recepcion(fotos=demasiadas))
        self.assertContains(r, 'máximo 8 fotos')
        self.assertEqual(OrdenServicio.objects.count(), antes)

    def test_formulario_en_espanol(self):
        self.entrar(self.recepcion)
        r = self.client.get(reverse('orden_create') + f'?equipo={self.equipo.pk}')
        self.assertNotContains(r, 'Select an option')
        self.assertContains(r, 'Técnico asignado')
        self.assertContains(r, 'Sin asignar por ahora')

    def test_tecnico_actualiza_y_usa_repuesto(self):
        self.entrar(self.tecnico)
        r = self.client.post(reverse('orden_actualizar', args=[self.orden.pk]), {
            'estado': 'en_reparacion', 'diagnostico_tecnico': 'Pantalla dañada',
            'costo_estimado': '300', 'costo_final': '350',
        })
        self.assertEqual(r.status_code, 302)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, 'en_reparacion')
        self.client.post(
            reverse('repuesto_agregar', args=[self.orden.pk]), {'producto': self.pantalla.pk, 'cantidad': 1},
        )
        self.pantalla.refresh_from_db()
        self.assertEqual(self.pantalla.stock_actual, 2)

    def test_tecnico_no_toca_orden_ajena(self):
        self.entrar(self.otro_tecnico)
        r = self.client.post(reverse('orden_actualizar', args=[self.orden.pk]), {'estado': 'cancelado'})
        self.assertEqual(r.status_code, 403)

    def test_no_se_puede_marcar_entregado_a_mano(self):
        self.entrar(self.admin)
        self.client.post(reverse('orden_actualizar', args=[self.orden.pk]), {
            'estado': 'entregado', 'costo_estimado': '0', 'costo_final': '0',
        })
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.estado, 'recibido')

    def test_subir_evidencia(self):
        self.entrar(self.recepcion)
        foto = SimpleUploadedFile('f.png', imagen_png(), content_type='image/png')
        self.client.post(reverse('evidencia_create', args=[self.orden.pk]), {
            'momento': 'recepcion', 'url_foto': foto, 'descripcion': 'Rayón',
        })
        self.assertEqual(self.orden.evidencias.count(), 1)
        self.assertEqual(self.client.get(reverse('orden_detail', args=[self.orden.pk])).status_code, 200)

    def test_pos_cobra_orden_con_productos(self):
        self.orden.estado = 'listo_entrega'
        self.orden.costo_final = 300
        self.orden.save()
        self.entrar(self.recepcion)
        r = self.client.post(reverse('venta_create') + f'?orden={self.orden.pk}', {
            'metodo_pago': 'efectivo',
            'lineas-TOTAL_FORMS': '2', 'lineas-INITIAL_FORMS': '0',
            'lineas-MIN_NUM_FORMS': '0', 'lineas-MAX_NUM_FORMS': '1000',
            'lineas-0-producto': self.cargador.pk, 'lineas-0-cantidad': '2',
            'lineas-1-producto': '', 'lineas-1-cantidad': '1',
        })
        self.assertEqual(r.status_code, 302)
        self.orden.refresh_from_db()
        self.assertEqual(self.orden.venta.total, Decimal('400'))
