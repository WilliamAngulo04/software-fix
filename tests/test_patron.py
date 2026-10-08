from django import forms
from django.test import SimpleTestCase
from django.urls import reverse

from clientes import patron
from ordenes.models import OrdenServicio

from .test_flujo import Base


class ValidarPatronTests(SimpleTestCase):
    def test_validos(self):
        for valor in ('1478', '14789', '123456789', '5193'):
            with self.subTest(valor=valor):
                self.assertEqual(patron.validar(valor), valor)
        self.assertIsNone(patron.validar(''))

    def test_invalidos(self):
        for valor, mensaje in [('123', 'al menos 4'), ('1231', 'repetir'), ('12a4', 'del 1 al 9'), ('0123', 'del 1 al 9')]:
            with self.subTest(valor=valor), self.assertRaisesMessage(forms.ValidationError, mensaje):
                patron.validar(valor)

    def test_svg_marca_orden_e_inicio(self):
        dibujo = patron.svg('14789')
        self.assertIn('points="50,50 50,150 50,250 150,250 250,250"', dibujo)
        self.assertIn('stroke="#198754"', dibujo)  # círculo de inicio
        self.assertEqual(dibujo.count('<text'), 5)


class PatronEnOrdenTests(Base):
    def test_recepcion_guarda_patron_y_lo_muestra_sin_imprimirlo(self):
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse('orden_create'))
        self.assertContains(r, 'patron-editor')
        self.assertContains(r, 'js/patron.js')

        self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk, 'modo_equipo': 'nuevo',
            'eq-tipo_dispositivo': 'celular', 'eq-marca': 'Xiaomi', 'eq-modelo': 'Redmi 12',
            'eq-patron': '14789', 'falla_reportada': 'No carga', 'costo_estimado': '0',
        })
        orden = OrdenServicio.objects.latest('id')
        self.assertEqual(orden.equipo.patron, '14789')

        detalle = self.client.get(reverse('orden_detail', args=[orden.pk]))
        self.assertContains(detalle, 'aria-label="Patrón 14789"')
        comprobante = self.client.get(reverse('orden_comprobante', args=[orden.pk]))
        self.assertNotContains(comprobante, '14789')

    def test_patron_invalido_no_crea_la_orden(self):
        self.client.force_login(self.recepcion)
        antes = OrdenServicio.objects.count()
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk, 'modo_equipo': 'nuevo',
            'eq-tipo_dispositivo': 'celular', 'eq-marca': 'X', 'eq-modelo': 'Y',
            'eq-patron': '12', 'falla_reportada': 'x', 'costo_estimado': '0',
        })
        self.assertContains(r, 'al menos 4 puntos')
        self.assertEqual(OrdenServicio.objects.count(), antes)

    def test_equipo_registrado_muestra_y_actualiza_desbloqueo(self):
        self.equipo.clave_patron = '1111'
        self.equipo.patron = '1235'
        self.equipo.save()
        self.client.force_login(self.recepcion)

        r = self.client.get(reverse('orden_create'))
        # El formulario trae los datos guardados para cargarlos al elegir el equipo.
        self.assertContains(r, 'desbloqueo-existente')
        self.assertContains(r, '"patron": "1235"')

        self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk,
            'modo_equipo': 'existente', 'equipo': self.equipo.pk,
            'clave_existente': '2222', 'patron_existente': '75319',
            'falla_reportada': 'x', 'costo_estimado': '0',
        })
        self.equipo.refresh_from_db()
        self.assertEqual((self.equipo.clave_patron, self.equipo.patron), ('2222', '75319'))

    def test_equipo_registrado_con_patron_invalido(self):
        self.client.force_login(self.recepcion)
        r = self.client.post(reverse('orden_create'), {
            'modo_cliente': 'existente', 'cliente': self.cliente.pk,
            'modo_equipo': 'existente', 'equipo': self.equipo.pk,
            'patron_existente': '11', 'falla_reportada': 'x', 'costo_estimado': '0',
        })
        self.assertContains(r, 'no puede repetir puntos')

    def test_editar_equipo_conserva_el_patron(self):
        self.equipo.patron = '3578'
        self.equipo.save()
        self.client.force_login(self.recepcion)
        r = self.client.get(reverse('equipo_update', args=[self.equipo.pk]))
        self.assertContains(r, 'value="3578"')
