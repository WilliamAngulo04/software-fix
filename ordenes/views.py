from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from clientes.forms import ClienteForm, EquipoForm
from clientes.models import Cliente, Equipo
from cuentas.permisos import ADMIN, RECEPCION, TECNICO, RolRequeridoMixin

from . import services
from .forms import EvidenciaForm, OrdenForm, OrdenGestionForm, RecepcionForm, RepuestoForm
from .models import DetalleReparacionRepuesto, OrdenServicio


def puede_gestionar(usuario, orden):
    """Admin y recepción gestionan cualquier orden; el técnico solo las suyas o las sin asignar."""
    if usuario.es_admin or usuario.es_recepcion:
        return True
    return usuario.es_tecnico and orden.tecnico_id in (None, usuario.pk)


def puede_usar_repuestos(usuario, orden):
    return (usuario.es_admin or usuario.es_tecnico) and puede_gestionar(usuario, orden)


class OrdenListView(RolRequeridoMixin, ListView):
    model = OrdenServicio
    campo_establecimiento = 'establecimiento'
    template_name = 'ordenes/orden_list.html'
    context_object_name = 'ordenes'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related('equipo__cliente', 'tecnico')
        g = self.request.GET
        if g.get('estado') == 'abiertas':
            qs = qs.exclude(estado__in=OrdenServicio.ESTADOS_CERRADOS)
        elif g.get('estado'):
            qs = qs.filter(estado=g['estado'])
        if g.get('mias'):
            qs = qs.filter(tecnico=self.request.user)
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(codigo_orden__icontains=q) | Q(equipo__cliente__nombre__icontains=q)
                | Q(equipo__cliente__documento_id__icontains=q) | Q(equipo__marca__icontains=q)
                | Q(equipo__modelo__icontains=q) | Q(equipo__numero_serie_imei__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = OrdenServicio.Estado.choices
        ctx['ahora'] = timezone.now()
        return ctx


class OrdenCreateView(RolRequeridoMixin, View):
    """
    Recepción de un equipo en una sola pantalla: cliente (registrado o nuevo),
    equipo (registrado o nuevo) y datos de la orden.
    """

    roles = (ADMIN, RECEPCION)
    template_name = 'ordenes/orden_form.html'

    def formularios(self, datos=None, inicial=None):
        e = self.establecimiento
        return {
            'recepcion': RecepcionForm(datos, establecimiento=e, initial=inicial),
            'cliente_form': ClienteForm(datos, establecimiento=e, prefix='cli'),
            'equipo_form': EquipoForm(datos, prefix='eq'),
            'orden_form': OrdenForm(datos, establecimiento=e),
        }

    def mostrar(self, request, forms):
        recepcion = forms['recepcion']
        # Relación equipo → cliente para filtrar la lista de equipos en el navegador.
        equipos_por_cliente = {
            str(pk): cliente_id
            for pk, cliente_id in recepcion.fields['equipo'].queryset.values_list('pk', 'cliente_id')
        }
        return render(request, self.template_name, {**forms, 'equipos_por_cliente': equipos_por_cliente})

    def get(self, request):
        inicial = {}
        if request.GET.get('cliente'):
            cliente = get_object_or_404(Cliente, pk=request.GET['cliente'], establecimiento=self.establecimiento)
            inicial.update(modo_cliente=RecepcionForm.EXISTENTE, cliente=cliente)
        if request.GET.get('equipo'):
            equipo = get_object_or_404(
                Equipo, pk=request.GET['equipo'], cliente__establecimiento=self.establecimiento,
            )
            inicial.update(
                modo_cliente=RecepcionForm.EXISTENTE, cliente=equipo.cliente,
                modo_equipo=RecepcionForm.EXISTENTE, equipo=equipo,
            )
        return self.mostrar(request, self.formularios(inicial=inicial))

    def post(self, request):
        forms = self.formularios(request.POST)
        recepcion, cliente_form, equipo_form, orden_form = (
            forms['recepcion'], forms['cliente_form'], forms['equipo_form'], forms['orden_form'],
        )
        validos = [recepcion.is_valid(), orden_form.is_valid()]
        if recepcion.is_valid():
            datos = recepcion.cleaned_data
            if datos['modo_cliente'] == RecepcionForm.NUEVO:
                validos.append(cliente_form.is_valid())
            if datos['modo_equipo'] == RecepcionForm.NUEVO:
                validos.append(equipo_form.is_valid())
        if not all(validos):
            messages.error(request, 'Revisa los campos marcados en rojo.')
            return self.mostrar(request, forms)

        with transaction.atomic():
            datos = recepcion.cleaned_data
            if datos['modo_cliente'] == RecepcionForm.NUEVO:
                cliente_form.instance.establecimiento = self.establecimiento
                cliente = cliente_form.save()
            else:
                cliente = datos['cliente']
            if datos['modo_equipo'] == RecepcionForm.NUEVO:
                equipo_form.instance.cliente = cliente
                equipo = equipo_form.save()
            else:
                equipo = datos['equipo']
            orden = orden_form.save(commit=False)
            orden.establecimiento = self.establecimiento
            orden.equipo = equipo
            orden.recepcionista = request.user
            orden.save()

        messages.success(request, f'Orden {orden.codigo_orden} creada. Agrega las fotos de recepción.')
        return redirect('orden_detail', pk=orden.pk)


class OrdenDetailView(RolRequeridoMixin, DetailView):
    model = OrdenServicio
    campo_establecimiento = 'establecimiento'
    template_name = 'ordenes/orden_detail.html'
    context_object_name = 'orden'

    def get_queryset(self):
        return super().get_queryset().select_related('equipo__cliente', 'tecnico', 'recepcionista')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        orden, usuario = self.object, self.request.user
        ctx['puede_gestionar'] = puede_gestionar(usuario, orden) and not orden.cerrada
        ctx['puede_repuestos'] = puede_usar_repuestos(usuario, orden) and not orden.cerrada
        ctx['puede_cobrar'] = (
            (usuario.es_admin or usuario.es_recepcion)
            and orden.estado == OrdenServicio.Estado.LISTO_ENTREGA and not orden.esta_cobrada
        )
        if ctx['puede_gestionar']:
            ctx['gestion_form'] = OrdenGestionForm(instance=orden, puede_asignar=not usuario.es_tecnico)
        if ctx['puede_repuestos']:
            ctx['repuesto_form'] = RepuestoForm(establecimiento=self.establecimiento)
        ctx['evidencia_form'] = EvidenciaForm()
        ctx['repuestos'] = orden.repuestos.select_related('producto')
        ctx['evidencias'] = orden.evidencias.select_related('usuario')
        return ctx


class OrdenAccionMixin(RolRequeridoMixin):
    """Base para las acciones POST sobre una orden."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        self.orden = get_object_or_404(OrdenServicio, pk=kwargs['pk'], establecimiento=self.establecimiento)
        return self.accion(request, *args, **kwargs)

    def volver(self):
        return redirect('orden_detail', pk=self.orden.pk)


class OrdenActualizarView(OrdenAccionMixin, View):
    def accion(self, request, pk):
        if not puede_gestionar(request.user, self.orden) or self.orden.cerrada:
            raise PermissionDenied
        form = OrdenGestionForm(request.POST, instance=self.orden, puede_asignar=not request.user.es_tecnico)
        if form.is_valid():
            orden = form.save(commit=False)
            # Un técnico que trabaja una orden sin asignar se la queda.
            if request.user.es_tecnico and orden.tecnico_id is None:
                orden.tecnico = request.user
            orden.save()
            messages.success(request, 'Orden actualizada.')
        else:
            errores = '; '.join(f'{form.fields[c].label if c in form.fields else c}: {", ".join(e)}'
                                for c, e in form.errors.items())
            messages.error(request, f'No se pudo actualizar: {errores}')
        return self.volver()


class EvidenciaCreateView(OrdenAccionMixin, View):
    def accion(self, request, pk):
        form = EvidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            evidencia = form.save(commit=False)
            evidencia.orden = self.orden
            evidencia.usuario = request.user
            evidencia.save()
            messages.success(request, 'Foto agregada.')
        else:
            messages.error(request, 'Selecciona una imagen válida.')
        return redirect(reverse('orden_detail', args=[pk]) + '#evidencias')


class RepuestoAgregarView(OrdenAccionMixin, View):
    roles = (ADMIN, TECNICO)

    def accion(self, request, pk):
        if not puede_usar_repuestos(request.user, self.orden):
            raise PermissionDenied
        form = RepuestoForm(request.POST, establecimiento=self.establecimiento)
        if form.is_valid():
            try:
                services.agregar_repuesto(self.orden, form.cleaned_data['producto'], form.cleaned_data['cantidad'])
                messages.success(request, 'Repuesto agregado y descontado del inventario.')
            except ValidationError as error:
                messages.error(request, error.messages[0])
        else:
            messages.error(request, 'Revisa el producto y la cantidad.')
        return redirect(reverse('orden_detail', args=[pk]) + '#repuestos')


class RepuestoQuitarView(OrdenAccionMixin, View):
    roles = (ADMIN, TECNICO)

    def accion(self, request, pk, detalle_pk):
        if not puede_usar_repuestos(request.user, self.orden):
            raise PermissionDenied
        detalle = get_object_or_404(DetalleReparacionRepuesto, pk=detalle_pk, orden=self.orden)
        try:
            services.quitar_repuesto(detalle)
            messages.success(request, 'Repuesto devuelto al inventario.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
        return redirect(reverse('orden_detail', args=[pk]) + '#repuestos')


class OrdenComprobanteView(RolRequeridoMixin, DetailView):
    """Comprobante imprimible para entregar al cliente al recibir el equipo."""

    model = OrdenServicio
    campo_establecimiento = 'establecimiento'
    template_name = 'ordenes/orden_comprobante.html'
    context_object_name = 'orden'

    def get_queryset(self):
        return super().get_queryset().select_related('equipo__cliente', 'recepcionista', 'establecimiento')
