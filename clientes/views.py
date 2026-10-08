from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cuentas.permisos import ADMIN, RECEPCION, RolRequeridoMixin
from ordenes.models import OrdenServicio

from .forms import ClienteForm, EquipoForm
from .models import Cliente, Equipo

EDITORES = (ADMIN, RECEPCION)


class ClienteFormMixin:
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), 'establecimiento': self.establecimiento}


class ClienteListView(RolRequeridoMixin, ListView):
    model = Cliente
    campo_establecimiento = 'establecimiento'
    template_name = 'clientes/cliente_list.html'
    context_object_name = 'clientes'
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().annotate(num_equipos=Count('equipos')).order_by('nombre')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(nombre__icontains=q) | Q(documento_id__icontains=q)
                | Q(telefono__icontains=q) | Q(email__icontains=q)
            )
        return qs


class ClienteDetailView(RolRequeridoMixin, DetailView):
    model = Cliente
    campo_establecimiento = 'establecimiento'
    template_name = 'clientes/cliente_detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['equipos'] = self.object.equipos.all()
        ctx['ordenes'] = OrdenServicio.objects.filter(equipo__cliente=self.object).select_related('equipo', 'tecnico')
        return ctx


class ClienteCreateView(RolRequeridoMixin, ClienteFormMixin, CreateView):
    roles = EDITORES
    model = Cliente
    form_class = ClienteForm
    template_name = 'form_generico.html'
    extra_context = {'titulo': 'Nuevo cliente'}

    def form_valid(self, form):
        form.instance.establecimiento = self.establecimiento
        messages.success(self.request, 'Cliente registrado. Ahora agrega su equipo.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('equipo_create', args=[self.object.pk])


class ClienteUpdateView(RolRequeridoMixin, ClienteFormMixin, UpdateView):
    roles = EDITORES
    model = Cliente
    campo_establecimiento = 'establecimiento'
    form_class = ClienteForm
    template_name = 'form_generico.html'
    extra_context = {'titulo': 'Editar cliente'}

    def get_success_url(self):
        messages.success(self.request, 'Cliente actualizado.')
        return reverse('cliente_detail', args=[self.object.pk])


class EquipoCreateView(RolRequeridoMixin, CreateView):
    roles = EDITORES
    model = Equipo
    form_class = EquipoForm
    template_name = 'form_generico.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.establecimiento_id:
            self.cliente = get_object_or_404(
                Cliente, pk=kwargs['cliente_pk'], establecimiento_id=request.user.establecimiento_id,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Nuevo equipo de {self.cliente.nombre}'
        return ctx

    def form_valid(self, form):
        form.instance.cliente = self.cliente
        messages.success(self.request, 'Equipo registrado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('cliente_detail', args=[self.cliente.pk])


class EquipoUpdateView(RolRequeridoMixin, UpdateView):
    roles = EDITORES
    model = Equipo
    campo_establecimiento = 'cliente__establecimiento'
    form_class = EquipoForm
    template_name = 'form_generico.html'
    extra_context = {'titulo': 'Editar equipo'}

    def get_success_url(self):
        messages.success(self.request, 'Equipo actualizado.')
        return reverse('cliente_detail', args=[self.object.cliente_id])
