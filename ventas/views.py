from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from cuentas.permisos import ADMIN, RECEPCION, RolRequeridoMixin
from ordenes.models import OrdenServicio

from . import services
from .forms import LineaVentaFormSet, VentaForm
from .models import Venta

CAJEROS = (ADMIN, RECEPCION)


class VentaListView(RolRequeridoMixin, ListView):
    roles = CAJEROS
    model = Venta
    template_name = 'ventas/venta_list.html'
    context_object_name = 'ventas'
    paginate_by = 30

    def get_queryset(self):
        qs = Venta.objects.select_related('cliente', 'usuario', 'orden_servicio')
        g = self.request.GET
        if g.get('desde'):
            qs = qs.filter(fecha_venta__date__gte=g['desde'])
        if g.get('hasta'):
            qs = qs.filter(fecha_venta__date__lte=g['hasta'])
        if g.get('metodo'):
            qs = qs.filter(metodo_pago=g['metodo'])
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(Q(cliente__nombre__icontains=q) | Q(orden_servicio__codigo_orden__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['total_filtrado'] = self.object_list.aggregate(t=Sum('total'))['t'] or 0
        ctx['metodos'] = Venta.MetodoPago.choices
        return ctx


class VentaDetailView(RolRequeridoMixin, DetailView):
    roles = CAJEROS
    model = Venta
    template_name = 'ventas/venta_detail.html'

    def get_queryset(self):
        return Venta.objects.select_related('cliente', 'usuario', 'orden_servicio__equipo')


class VentaCreateView(RolRequeridoMixin, View):
    """Punto de venta. Con ?orden=<id> cobra una orden de servicio (más productos opcionales)."""

    roles = CAJEROS
    template_name = 'ventas/venta_form.html'

    def get_orden(self, request):
        orden_id = request.GET.get('orden')
        return get_object_or_404(OrdenServicio, pk=orden_id) if orden_id else None

    def mostrar(self, request, form, formset, orden):
        return render(request, self.template_name, {'form': form, 'formset': formset, 'orden': orden})

    def get(self, request):
        orden = self.get_orden(request)
        return self.mostrar(request, VentaForm(orden=orden), LineaVentaFormSet(prefix='lineas'), orden)

    def post(self, request):
        orden = self.get_orden(request)
        form = VentaForm(request.POST, orden=orden)
        formset = LineaVentaFormSet(request.POST, prefix='lineas')
        if form.is_valid() and formset.is_valid():
            items = [
                (f.cleaned_data['producto'], f.cleaned_data['cantidad'])
                for f in formset
                if f.cleaned_data and not f.cleaned_data.get('DELETE')
            ]
            try:
                venta = services.registrar_venta(
                    usuario=request.user,
                    metodo_pago=form.cleaned_data['metodo_pago'],
                    items=items,
                    cliente=form.cleaned_data.get('cliente'),
                    orden=orden,
                )
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, f'Venta #{venta.pk} registrada por ${venta.total:,.0f}.')
                return redirect('venta_detail', pk=venta.pk)
        return self.mostrar(request, form, formset, orden)
