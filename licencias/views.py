from django import forms
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.views.generic import TemplateView

from config.estilos import BootstrapMixin

from . import services
from .models import ConfiguracionPlataforma, Licencia, PlanLicencia


class SolicitudForm(BootstrapMixin, forms.Form):
    plan = forms.ModelChoiceField(queryset=PlanLicencia.objects.filter(activo=True), widget=forms.RadioSelect)
    referencia_pago = forms.CharField(
        label='Referencia del pago (opcional)', max_length=100, required=False,
        help_text='Número del comprobante, de la transferencia o de Nequi. Agiliza la activación.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].label_from_instance = (
            lambda p: f'{p.nombre} · {p.dias} días · ${p.precio:,.0f}'.replace(',', '.')
        )


class PlanesView(TemplateView):
    """Página pública con los planes ("Adquiere tu licencia aquí")."""

    template_name = 'licencias/planes.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        planes = list(PlanLicencia.objects.filter(activo=True))
        if planes:
            base = max(p.precio_mensual for p in planes)
            for p in planes:
                p.ahorro = round((1 - p.precio_mensual / base) * 100) if base else 0
        ctx['planes'] = planes
        ctx['config'] = ConfiguracionPlataforma.obtener()
        return ctx


class MiLicenciaView(LoginRequiredMixin, TemplateView):
    """Estado de la licencia del taller, historial y solicitud de un plan (solo administradores)."""

    template_name = 'licencias/mi_licencia.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.establecimiento_id:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, form=None, **kwargs):
        ctx = super().get_context_data(**kwargs)
        taller = self.request.user.establecimiento
        ctx['taller'] = taller
        ctx['historial'] = taller.licencias.select_related('plan')
        ctx['pendiente'] = taller.licencias.filter(estado=Licencia.Estado.PENDIENTE).first()
        ctx['config'] = ConfiguracionPlataforma.obtener()
        ctx['form'] = form or SolicitudForm()
        return ctx

    def post(self, request):
        if not request.user.es_admin:
            messages.error(request, 'Solo el administrador del taller puede adquirir la licencia.')
            return redirect('mi_licencia')
        form = SolicitudForm(request.POST)
        if form.is_valid():
            try:
                services.solicitar(
                    request.user.establecimiento, form.cleaned_data['plan'], request.user,
                    form.cleaned_data['referencia_pago'],
                )
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, 'Solicitud enviada. Activaremos tu licencia en cuanto confirmemos el pago.')
                return redirect('mi_licencia')
        return self.render_to_response(self.get_context_data(form=form))
