from datetime import timedelta

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Establecimiento, Usuario
from licencias import services
from licencias.models import Licencia, PlanLicencia

from .test_flujo import Base

CLAVE = 'UnaClave-Segura-99'


class LicenciaTests(Base):
    def setUp(self):
        super().setUp()
        self.mensual = PlanLicencia.objects.get(nombre='Mensual')
        self.anual = PlanLicencia.objects.get(nombre='Anual')
        self.superusuario = Usuario.objects.create_superuser('su@x.com', 'Super', CLAVE)

    def vencer(self, taller=None):
        taller = taller or self.taller
        taller.licencia_hasta = timezone.now() - timedelta(minutes=1)
        taller.save()

    def test_planes_iniciales(self):
        self.assertEqual(
            list(PlanLicencia.objects.values_list('nombre', 'dias')),
            [('Mensual', 30), ('Trimestral', 90), ('Semestral', 180), ('Anual', 365)],
        )

    def test_registro_da_7_dias_de_prueba(self):
        self.client.post(reverse('registro'), {
            'taller': 'Nuevo', 'nombre': 'Dueño', 'email': 'n@x.com', 'password1': CLAVE, 'password2': CLAVE,
        })
        taller = Establecimiento.objects.get(nombre='Nuevo')
        self.assertEqual(taller.dias_restantes, 7)
        self.assertTrue(taller.en_prueba)

    def test_licencia_vencida_bloquea_el_sistema(self):
        self.vencer()
        for usuario in (self.admin, self.tecnico, self.recepcion):
            self.client.force_login(usuario)
            for url in (reverse('dashboard'), reverse('orden_list'), reverse('venta_create')):
                with self.subTest(rol=usuario.rol, url=url):
                    self.assertRedirects(self.client.get(url), reverse('mi_licencia'))
            r = self.client.get(reverse('mi_licencia'))
            self.assertContains(r, 'El acceso al sistema está bloqueado')

    def test_superusuario_nunca_se_bloquea(self):
        self.vencer(self.superusuario.establecimiento)
        self.client.force_login(self.superusuario)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        self.assertEqual(self.client.get('/admin/licencias/licencia/').status_code, 200)

    def test_solicitar_y_aprobar(self):
        self.vencer()
        self.client.force_login(self.admin)
        r = self.client.post(reverse('mi_licencia'), {'plan': self.mensual.pk, 'referencia_pago': ' NEQUI-123 '})
        self.assertRedirects(r, reverse('mi_licencia'))
        solicitud = Licencia.objects.get()
        self.assertEqual((solicitud.estado, solicitud.valor, solicitud.referencia_pago),
                         ('pendiente', self.mensual.precio, 'NEQUI-123'))
        # Sigue bloqueado hasta que el superusuario aprueba.
        self.assertRedirects(self.client.get(reverse('dashboard')), reverse('mi_licencia'))
        # No puede enviar otra mientras haya una pendiente.
        with self.assertRaises(ValidationError):
            services.solicitar(self.taller, self.anual, self.admin)

        # El superusuario aprueba desde el panel con la acción masiva.
        self.client.force_login(self.superusuario)
        self.client.post('/admin/licencias/licencia/', {
            'action': 'aprobar_seleccionadas', '_selected_action': [solicitud.pk],
        })
        self.taller.refresh_from_db()
        self.assertEqual(self.taller.dias_restantes, 30)
        self.assertFalse(self.taller.en_prueba)

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_renovar_antes_de_vencer_suma_los_dias(self):
        # Le quedan 30 días (Base) y compra un año: queda con 30 + 365.
        licencia = services.solicitar(self.taller, self.anual, self.admin)
        services.aprobar(licencia, self.superusuario)
        self.taller.refresh_from_db()
        self.assertEqual(self.taller.dias_restantes, 395)

    def test_superusuario_crea_licencia_directamente(self):
        self.vencer()
        self.client.force_login(self.superusuario)
        self.client.post('/admin/licencias/licencia/add/', {
            'establecimiento': self.taller.pk, 'plan': self.mensual.pk, 'estado': 'aprobada',
            'valor': '', 'referencia_pago': 'Efectivo', 'notas': '',
        })
        self.taller.refresh_from_db()
        self.assertEqual(self.taller.dias_restantes, 30)
        self.assertEqual(Licencia.objects.get().valor, self.mensual.precio)

    def test_solo_el_admin_del_taller_solicita(self):
        self.client.force_login(self.tecnico)
        self.client.post(reverse('mi_licencia'), {'plan': self.mensual.pk})
        self.assertFalse(Licencia.objects.exists())

    def test_aviso_de_vencimiento(self):
        self.taller.licencia_hasta = timezone.now() + timedelta(days=3)
        self.taller.save()
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse('dashboard'))
        self.assertContains(r, 'vence en')
        self.assertContains(r, 'Avisa al administrador')

    def test_paginas_publicas(self):
        r = self.client.get(reverse('login'))
        self.assertContains(r, 'Adquiere tu licencia aquí')
        self.assertContains(r, 'Consultar el estado de mi orden')
        r = self.client.get(reverse('planes'))
        self.assertContains(r, 'Trimestral')
        self.assertContains(r, '7 días gratis')


class ConsultaOrdenTests(Base):
    def setUp(self):
        super().setUp()
        cache.clear()  # El límite de intentos vive en la caché.
        self.cliente.telefono = '3001234567'
        self.cliente.save()
        self.equipo.clave_patron = 'SECRETA-9876'
        self.equipo.save()

    def consultar(self, codigo, dato):
        return self.client.post(reverse('consulta_orden'), {'codigo': codigo, 'dato': dato})

    def test_consulta_con_documento_o_telefono(self):
        for dato in ('123', '300 123 4567'):
            with self.subTest(dato=dato):
                r = self.consultar(self.orden.codigo_orden.lower(), dato)
                self.assertContains(r, self.orden.codigo_orden)
                self.assertContains(r, 'Taller Uno')
                self.assertNotContains(r, 'SECRETA-9876')

    def test_consulta_con_datos_incorrectos(self):
        r = self.consultar(self.orden.codigo_orden, '999')
        self.assertContains(r, 'No encontramos una orden')
        self.assertNotContains(r, 'Samsung')

    def test_limite_de_intentos(self):
        for _ in range(10):
            self.consultar('ORD-0000-0000', '1')
        r = self.consultar(self.orden.codigo_orden, '123')
        self.assertContains(r, 'Demasiados intentos')

    def test_consulta_funciona_aunque_la_licencia_venza(self):
        self.taller.licencia_hasta = timezone.now() - timedelta(days=1)
        self.taller.save()
        self.assertContains(self.consultar(self.orden.codigo_orden, '123'), self.orden.codigo_orden)
