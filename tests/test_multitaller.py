from django.core.exceptions import ValidationError
from django.urls import reverse

from clientes.models import Cliente, Equipo
from cuentas.models import Establecimiento, Usuario
from inventario.models import ProductoInventario
from ordenes.models import OrdenServicio
from ventas import services as venta_services

from .test_flujo import Base

CLAVE = 'UnaClave-Segura-99'


class RegistroTests(Base):
    def test_registro_crea_taller_y_admin(self):
        r = self.client.post(reverse('registro'), {
            'taller': 'Mi Taller Nuevo', 'telefono_taller': '555', 'nombre': 'Dueño',
            'email': 'Nuevo@X.com', 'password1': CLAVE, 'password2': CLAVE,
        })
        self.assertRedirects(r, reverse('usuario_list'))
        nuevo = Usuario.objects.get(email='nuevo@x.com')
        self.assertEqual(nuevo.rol, 'admin')
        self.assertEqual(nuevo.establecimiento.nombre, 'Mi Taller Nuevo')
        self.assertFalse(nuevo.is_staff)

        # Los usuarios que crea quedan en su taller.
        self.client.post(reverse('usuario_create'), {
            'nombre': 'Técnico nuevo', 'email': 'tn@x.com', 'rol': 'tecnico', 'activo': 'on',
            'password1': CLAVE, 'password2': CLAVE,
        })
        self.assertEqual(Usuario.objects.get(email='tn@x.com').establecimiento, nuevo.establecimiento)

    def test_registro_rechaza_email_repetido(self):
        r = self.client.post(reverse('registro'), {
            'taller': 'Repetido', 'nombre': 'Y', 'email': 'A@x.com', 'password1': CLAVE, 'password2': CLAVE,
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una cuenta con este email')
        self.assertFalse(Establecimiento.objects.filter(nombre='Repetido').exists())

    def test_registro_redirige_si_ya_hay_sesion(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse('registro')), reverse('dashboard'))

    def test_admin_de_taller_no_entra_al_panel_django(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get('/admin/').status_code, 302)

    def test_superusuario_queda_con_taller(self):
        su = Usuario.objects.create_superuser('su@x.com', 'Super', CLAVE)
        self.assertTrue(su.is_staff)
        self.assertEqual(su.establecimiento.nombre, 'Taller de Super')


class AislamientoTests(Base):
    """Cada taller solo ve y modifica sus propios datos."""

    def setUp(self):
        super().setUp()
        o = Establecimiento.objects.create(nombre='Taller Dos')
        self.admin2 = Usuario.objects.create_user('a2@x.com', 'Admin2', CLAVE, rol='admin', establecimiento=o)
        self.cliente2 = Cliente.objects.create(establecimiento=o, nombre='Beto', telefono='1', documento_id='123')
        self.equipo2 = Equipo.objects.create(cliente=self.cliente2, tipo_dispositivo='laptop', marca='HP', modelo='X')
        self.orden2 = OrdenServicio.objects.create(
            establecimiento=o, equipo=self.equipo2, recepcionista=self.admin2, falla_reportada='x',
        )
        self.producto2 = ProductoInventario.objects.create(
            establecimiento=o, nombre='Teclado', categoria='repuesto', precio_compra=1, precio_venta=2, stock_actual=5,
        )
        self.client.force_login(self.admin)

    def test_listas_solo_muestran_su_taller(self):
        self.assertNotContains(self.client.get(reverse('cliente_list')), 'Beto')
        self.assertNotContains(self.client.get(reverse('orden_list')), 'Beto')
        self.assertNotContains(self.client.get(reverse('producto_list')), 'Teclado')
        self.assertNotContains(self.client.get(reverse('usuario_list')), 'a2@x.com')
        self.assertNotContains(self.client.get(reverse('venta_create')), 'Teclado')
        self.assertNotContains(self.client.get(reverse('orden_create')), 'Beto')

    def test_no_accede_a_objetos_de_otro_taller(self):
        for url in [
            reverse('orden_detail', args=[self.orden2.pk]),
            reverse('orden_comprobante', args=[self.orden2.pk]),
            reverse('cliente_detail', args=[self.cliente2.pk]),
            reverse('cliente_update', args=[self.cliente2.pk]),
            reverse('equipo_create', args=[self.cliente2.pk]),
            reverse('equipo_update', args=[self.equipo2.pk]),
            reverse('producto_update', args=[self.producto2.pk]),
            reverse('usuario_update', args=[self.admin2.pk]),
            reverse('venta_create') + f'?orden={self.orden2.pk}',
            reverse('orden_create') + f'?cliente={self.cliente2.pk}',
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

        r = self.client.post(reverse('orden_actualizar', args=[self.orden2.pk]), {'estado': 'cancelado'})
        self.assertEqual(r.status_code, 404)
        self.orden2.refresh_from_db()
        self.assertEqual(self.orden2.estado, 'recibido')

    def test_no_usa_productos_ni_equipos_de_otro_taller(self):
        self.client.post(
            reverse('repuesto_agregar', args=[self.orden.pk]), {'producto': self.producto2.pk, 'cantidad': 1},
        )
        self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente2.pk,
            'modo_equipo': 'existente', 'equipo': self.equipo2.pk, 'falla_reportada': 'x', 'costo_estimado': '0',
        })
        self.producto2.refresh_from_db()
        self.assertEqual(self.producto2.stock_actual, 5)
        self.assertEqual(OrdenServicio.objects.filter(equipo=self.equipo2).count(), 1)
        with self.assertRaises(ValidationError):
            venta_services.registrar_venta(self.admin, 'efectivo', [(self.producto2, 1)])

    def test_consecutivo_y_documento_son_por_taller(self):
        # Ambos talleres tienen su propia orden 0001 y un cliente con documento 123.
        self.assertEqual(self.orden.codigo_orden, self.orden2.codigo_orden)
        r = self.client.post(reverse('cliente_create'), {'nombre': 'Repetido', 'telefono': '1', 'documento_id': '123'})
        self.assertContains(r, 'Ya existe un cliente con este documento')
