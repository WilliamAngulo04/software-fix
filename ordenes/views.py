from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from clientes.models import Cliente, Equipo
from cuentas.permisos import ADMIN, RECEPCION, TECNICO, RolRequeridoMixin

from . import services
from .forms import EvidenciaForm, OrdenForm, OrdenGestionForm, RepuestoForm
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


class OrdenCreateView(RolRequeridoMixin, CreateView):
    roles = (ADMIN, RECEPCION)
    model = OrdenServicio
    form_class = OrdenForm
    template_name = 'form_generico.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['establecimiento'] = self.establecimiento
        self.cliente = None
        if self.request.GET.get('cliente'):
            self.cliente = get_object_or_404(
                Cliente, pk=self.request.GET['cliente'], establecimiento=self.establecimiento,
            )
            kwargs['cliente'] = self.cliente
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('equipo'):
            initial['equipo'] = get_object_or_404(
                Equipo, pk=self.request.GET['equipo'], cliente__establecimiento=self.establecimiento,
            )
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nueva orden de servicio'
        if self.cliente:
            ctx['titulo'] += f' — {self.cliente.nombre}'
        ctx['ayuda'] = '¿El cliente o el equipo no existe? Regístralo primero en Clientes.'
        return ctx

    def form_valid(self, form):
        form.instance.establecimiento = self.establecimiento
        form.instance.recepcionista = self.request.user
        respuesta = super().form_valid(form)
        messages.success(self.request, f'Orden {self.object.codigo_orden} creada. Agrega las fotos de recepción.')
        return respuesta

    def get_success_url(self):
        return reverse('orden_detail', args=[self.object.pk])


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
