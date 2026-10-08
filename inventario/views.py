from django.contrib import messages
from django.db.models import F, Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from cuentas.permisos import ADMIN, RolRequeridoMixin

from .forms import ProductoForm
from .models import ProductoInventario


class ProductoListView(RolRequeridoMixin, ListView):
    model = ProductoInventario
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    paginate_by = 30

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_barras__icontains=q))
        categoria = self.request.GET.get('categoria')
        if categoria:
            qs = qs.filter(categoria=categoria)
        if self.request.GET.get('stock_bajo'):
            qs = qs.filter(stock_actual__lte=F('stock_minimo'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categorias'] = ProductoInventario.Categoria.choices
        return ctx


class ProductoCreateView(RolRequeridoMixin, CreateView):
    roles = (ADMIN,)
    model = ProductoInventario
    form_class = ProductoForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('producto_list')
    extra_context = {'titulo': 'Nuevo producto'}

    def form_valid(self, form):
        messages.success(self.request, 'Producto creado.')
        return super().form_valid(form)


class ProductoUpdateView(RolRequeridoMixin, UpdateView):
    roles = (ADMIN,)
    model = ProductoInventario
    form_class = ProductoForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('producto_list')
    extra_context = {'titulo': 'Editar producto'}

    def form_valid(self, form):
        messages.success(self.request, 'Producto actualizado.')
        return super().form_valid(form)
