from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.db.models import Count, F, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from inventario.models import ProductoInventario
from ordenes.models import OrdenServicio
from ventas.models import Venta

from .forms import LoginForm, UsuarioForm
from .models import Usuario
from .permisos import ADMIN, RolRequeridoMixin


class LoginView(auth_views.LoginView):
    template_name = 'cuentas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class DashboardView(RolRequeridoMixin, TemplateView):
    template_name = 'cuentas/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario = self.request.user
        abiertas = OrdenServicio.objects.exclude(estado__in=OrdenServicio.ESTADOS_CERRADOS)

        conteo = dict(abiertas.values_list('estado').annotate(n=Count('id')))
        ctx['por_estado'] = [
            (valor, etiqueta, conteo.get(valor, 0))
            for valor, etiqueta in OrdenServicio.Estado.choices
            if valor not in OrdenServicio.ESTADOS_CERRADOS
        ]
        ctx['total_abiertas'] = abiertas.count()
        ctx['vencidas'] = abiertas.filter(fecha_promesa__lt=timezone.now()).count()

        recientes = abiertas.select_related('equipo__cliente', 'tecnico')
        if usuario.es_tecnico:
            recientes = recientes.filter(tecnico=usuario)
        ctx['ordenes_recientes'] = recientes[:10]

        if not usuario.es_tecnico:
            hoy = Venta.objects.filter(fecha_venta__date=timezone.localdate())
            ctx['ventas_hoy_total'] = hoy.aggregate(t=Sum('total'))['t'] or 0
            ctx['ventas_hoy_cantidad'] = hoy.count()
        ctx['stock_bajo'] = ProductoInventario.objects.filter(stock_actual__lte=F('stock_minimo'))[:10]
        return ctx


class UsuarioListView(RolRequeridoMixin, ListView):
    roles = (ADMIN,)
    model = Usuario
    template_name = 'cuentas/usuario_list.html'
    context_object_name = 'usuarios'


class UsuarioCreateView(RolRequeridoMixin, CreateView):
    roles = (ADMIN,)
    model = Usuario
    form_class = UsuarioForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('usuario_list')
    extra_context = {'titulo': 'Nuevo usuario'}

    def form_valid(self, form):
        messages.success(self.request, 'Usuario creado.')
        return super().form_valid(form)


class UsuarioUpdateView(RolRequeridoMixin, UpdateView):
    roles = (ADMIN,)
    model = Usuario
    form_class = UsuarioForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('usuario_list')
    extra_context = {'titulo': 'Editar usuario'}

    def form_valid(self, form):
        if form.instance == self.request.user and (not form.instance.activo or not form.instance.es_admin):
            form.add_error(None, 'No puedes desactivarte ni quitarte el rol de administrador a ti mismo.')
            return self.form_invalid(form)
        messages.success(self.request, 'Usuario actualizado.')
        return super().form_valid(form)
