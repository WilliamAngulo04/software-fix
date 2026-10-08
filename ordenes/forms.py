from django import forms

from clientes.models import Cliente, Equipo
from config.estilos import BootstrapMixin, FechaHoraInput
from cuentas.models import Usuario
from inventario.models import ProductoInventario

from .models import EvidenciaFotografica, OrdenServicio


def tecnicos_activos(establecimiento):
    return Usuario.objects.filter(establecimiento=establecimiento, rol=Usuario.Rol.TECNICO, activo=True)


def etiqueta_producto(p):
    return f'{p.nombre} — ${p.precio_venta:,.0f} (stock: {p.stock_actual})'


class RecepcionForm(BootstrapMixin, forms.Form):
    """
    Primera parte de la recepción: decide si el cliente y el equipo ya existen o se
    registran en ese momento (los datos nuevos los validan ClienteForm y EquipoForm).
    """

    EXISTENTE, NUEVO = 'existente', 'nuevo'

    modo_cliente = forms.ChoiceField(
        choices=[(EXISTENTE, 'Cliente registrado'), (NUEVO, 'Cliente nuevo')], widget=forms.RadioSelect,
    )
    cliente = forms.ModelChoiceField(queryset=Cliente.objects.none(), required=False, label='Cliente')
    modo_equipo = forms.ChoiceField(
        choices=[(EXISTENTE, 'Equipo ya registrado'), (NUEVO, 'Equipo nuevo')], widget=forms.RadioSelect,
    )
    equipo = forms.ModelChoiceField(queryset=Equipo.objects.none(), required=False, label='Equipo')

    def __init__(self, *args, establecimiento, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.filter(establecimiento=establecimiento)
        self.fields['cliente'].label_from_instance = lambda c: ' · '.join(
            filter(None, [c.nombre, c.documento_id, c.telefono])
        )
        self.fields['equipo'].queryset = Equipo.objects.filter(cliente__establecimiento=establecimiento)
        self.fields['equipo'].label_from_instance = lambda e: (
            f'{e}{f" · {e.numero_serie_imei}" if e.numero_serie_imei else ""}'
        )
        hay_clientes = self.fields['cliente'].queryset.exists()
        self.fields['modo_cliente'].initial = self.EXISTENTE if hay_clientes else self.NUEVO
        self.fields['modo_equipo'].initial = self.EXISTENTE if hay_clientes else self.NUEVO

    def clean(self):
        datos = super().clean()
        cliente_nuevo = datos.get('modo_cliente') == self.NUEVO
        if cliente_nuevo:
            # Un cliente nuevo no tiene equipos registrados todavía.
            datos['modo_equipo'] = self.NUEVO
        elif not datos.get('cliente'):
            self.add_error('cliente', 'Selecciona el cliente.')

        if datos.get('modo_equipo') == self.EXISTENTE:
            equipo = datos.get('equipo')
            if not equipo:
                self.add_error('equipo', 'Selecciona el equipo.')
            elif datos.get('cliente') and equipo.cliente_id != datos['cliente'].pk:
                self.add_error('equipo', 'Ese equipo no pertenece al cliente seleccionado.')
        return datos


MAX_FOTOS_RECEPCION = 8
MAX_BYTES_FOTO = 4 * 1024 * 1024


class VariasImagenesInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VariasImagenesField(forms.ImageField):
    """Campo que acepta varias imágenes y valida cada una (formato y tamaño)."""

    def __init__(self, *args, **kwargs):
        # El input nativo queda oculto: la plantilla muestra un botón y miniaturas.
        kwargs.setdefault('widget', VariasImagenesInput(
            attrs={'accept': 'image/*', 'multiple': True, 'class': 'visually-hidden'},
        ))
        super().__init__(*args, **kwargs)

    def clean(self, datos, inicial=None):
        archivos = datos if isinstance(datos, (list, tuple)) else ([datos] if datos else [])
        if len(archivos) > MAX_FOTOS_RECEPCION:
            raise forms.ValidationError(f'Puedes subir máximo {MAX_FOTOS_RECEPCION} fotos.')
        limpios = []
        for archivo in archivos:
            if archivo.size > MAX_BYTES_FOTO:
                raise forms.ValidationError(f'La foto "{archivo.name}" pesa más de 4 MB.')
            limpios.append(super().clean(archivo, inicial))
        return limpios


class FotosRecepcionForm(BootstrapMixin, forms.Form):
    fotos = VariasImagenesField(label='Fotos del equipo', required=False)
    descripcion_fotos = forms.CharField(
        label='Nota para las fotos', max_length=255, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Ej: rayón en la esquina, pantalla encendida…'}),
    )


class OrdenForm(BootstrapMixin, forms.ModelForm):
    """Datos de la orden en la recepción."""

    class Meta:
        model = OrdenServicio
        fields = ['tecnico', 'falla_reportada', 'observaciones_esteticas', 'costo_estimado', 'fecha_promesa']
        labels = {'tecnico': 'Técnico asignado'}
        widgets = {'fecha_promesa': FechaHoraInput()}

    def __init__(self, *args, establecimiento, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = tecnicos_activos(establecimiento)
        self.fields['tecnico'].empty_label = 'Sin asignar por ahora'
        self.fields['falla_reportada'].widget.attrs['placeholder'] = 'Ej: no enciende, pantalla rota, no carga…'

    def clean_costo_estimado(self):
        costo = self.cleaned_data['costo_estimado']
        if costo is not None and costo < 0:
            raise forms.ValidationError('No puede ser negativo.')
        return costo


class OrdenGestionForm(BootstrapMixin, forms.ModelForm):
    """Actualización del trabajo técnico: estado, diagnóstico, costos y fechas."""

    class Meta:
        model = OrdenServicio
        fields = [
            'estado', 'tecnico', 'diagnostico_tecnico', 'observaciones_esteticas',
            'costo_estimado', 'costo_final', 'fecha_promesa',
        ]
        labels = {'tecnico': 'Técnico'}
        widgets = {'fecha_promesa': FechaHoraInput()}

    def __init__(self, *args, puede_asignar=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tecnico'].queryset = tecnicos_activos(self.instance.establecimiento_id)
        # "Entregado" solo se alcanza al cobrar la orden en Ventas.
        self.fields['estado'].choices = [
            c for c in OrdenServicio.Estado.choices
            if c[0] != OrdenServicio.Estado.ENTREGADO or self.instance.estado == c[0]
        ]
        if not puede_asignar:
            del self.fields['tecnico']

    def clean(self):
        datos = super().clean()
        for campo in ('costo_estimado', 'costo_final'):
            if datos.get(campo) is not None and datos[campo] < 0:
                self.add_error(campo, 'No puede ser negativo.')
        return datos


class EvidenciaForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = EvidenciaFotografica
        fields = ['momento', 'url_foto', 'descripcion']
        widgets = {'url_foto': forms.ClearableFileInput(attrs={'accept': 'image/*', 'capture': 'environment'})}


class RepuestoForm(BootstrapMixin, forms.Form):
    producto = forms.ModelChoiceField(queryset=ProductoInventario.objects.none())
    cantidad = forms.IntegerField(min_value=1, initial=1)

    def __init__(self, *args, establecimiento, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = (
            ProductoInventario.objects.filter(establecimiento=establecimiento, stock_actual__gt=0)
            .order_by('-es_repuesto', 'nombre')
        )
        self.fields['producto'].label_from_instance = etiqueta_producto
