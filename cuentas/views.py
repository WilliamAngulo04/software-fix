from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.db import transaction
from django.db.models import Count, F, Sum
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView

from inventario.models import ProductoInventario
from licencias import services as licencias
from ordenes.models import OrdenServicio
from ventas.models import Venta

from .forms import EstablecimientoForm, LoginForm, RegistroForm, UsuarioForm
from .models import Establecimiento, Usuario
from .permisos import ADMIN, RolRequeridoMixin


class LoginView(auth_views.LoginView):
    template_name = 'cuentas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class RegistroView(FormView):
    """Registro público de un taller nuevo con su administrador."""

    template_name = 'cuentas/registro.html'
    form_class = RegistroForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        datos = form.cleaned_data
        taller = Establecimiento.objects.create(nombre=datos['taller'], telefono=datos['telefono_taller'] or None)
        licencias.iniciar_prueba(taller)
        usuario = Usuario.objects.create_user(
            datos['email'], datos['nombre'], datos['password1'], rol=Usuario.Rol.ADMIN, establecimiento=taller,
        )
        login(self.request, usuario, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(
            self.request,
            f'¡Bienvenido! {taller.nombre} quedó registrado con {taller.dias_restantes} días de prueba gratis. '
            'Empieza creando a tu equipo de trabajo.',
        )
        return redirect('usuario_list')


class DashboardView(RolRequeridoMixin, TemplateView):
    template_name = 'cuentas/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        usuario, taller = self.request.user, self.establecimiento
        abiertas = OrdenServicio.objects.filter(establecimiento=taller).exclude(
            estado__in=OrdenServicio.ESTADOS_CERRADOS,
        )

        conteo = dict(abiertas.values_list('estado').annotate(n=Count('id')).order_by())
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
            hoy = Venta.objects.filter(establecimiento=taller, fecha_venta__date=timezone.localdate())
            ctx['ventas_hoy_total'] = hoy.aggregate(t=Sum('total'))['t'] or 0
            ctx['ventas_hoy_cantidad'] = hoy.count()
        ctx['stock_bajo'] = ProductoInventario.objects.filter(
            establecimiento=taller, stock_actual__lte=F('stock_minimo'),
        )[:10]
        ctx['sin_equipo'] = usuario.es_admin and not taller.usuarios.exclude(pk=usuario.pk).exists()
        return ctx


class UsuarioListView(RolRequeridoMixin, ListView):
    roles = (ADMIN,)
    model = Usuario
    campo_establecimiento = 'establecimiento'
    template_name = 'cuentas/usuario_list.html'
    context_object_name = 'usuarios'


class UsuarioCreateView(RolRequeridoMixin, CreateView):
    roles = (ADMIN,)
    model = Usuario
    form_class = UsuarioForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('usuario_list')
    extra_context = {'titulo': 'Nuevo usuario', 'ayuda': 'Crea las cuentas de tus técnicos y recepcionistas.'}

    def form_valid(self, form):
        form.instance.establecimiento = self.establecimiento
        messages.success(self.request, 'Usuario creado.')
        return super().form_valid(form)


class UsuarioUpdateView(RolRequeridoMixin, UpdateView):
    roles = (ADMIN,)
    model = Usuario
    campo_establecimiento = 'establecimiento'
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


class EstablecimientoUpdateView(RolRequeridoMixin, UpdateView):
    roles = (ADMIN,)
    form_class = EstablecimientoForm
    template_name = 'form_generico.html'
    success_url = reverse_lazy('dashboard')
    extra_context = {
        'titulo': 'Datos de mi taller',
        'ayuda': 'Aparecen en los comprobantes de orden y en los recibos de venta.',
    }

    def get_object(self, queryset=None):
        return self.establecimiento

    def form_valid(self, form):
        messages.success(self.request, 'Datos del taller actualizados.')
        return super().form_valid(form)
