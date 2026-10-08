from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from cuentas.models import Establecimiento

from .models import ConfiguracionPlataforma, Licencia


def iniciar_prueba(establecimiento):
    """Da al taller recién registrado sus días de prueba gratis."""
    dias = ConfiguracionPlataforma.obtener().dias_prueba
    establecimiento.licencia_hasta = timezone.now() + timedelta(days=dias)
    establecimiento.save(update_fields=['licencia_hasta'])


def solicitar(establecimiento, plan, usuario, referencia_pago=''):
    """El taller pide un plan; queda pendiente hasta que el superusuario confirme el pago."""
    if not plan.activo:
        raise ValidationError('Ese plan ya no está disponible.')
    if establecimiento.licencias.filter(estado=Licencia.Estado.PENDIENTE).exists():
        raise ValidationError('Ya tienes una solicitud pendiente. Espera a que la revisemos.')
    return Licencia.objects.create(
        establecimiento=establecimiento, plan=plan, valor=plan.precio,
        referencia_pago=referencia_pago.strip(), solicitada_por=usuario,
    )


@transaction.atomic
def aprobar(licencia, usuario):
    """
    Activa la licencia. Si el taller todavía tenía días vigentes, el plan se suma
    a partir de su vencimiento actual; si no, empieza ahora.
    """
    licencia = Licencia.objects.select_for_update().select_related('plan').get(pk=licencia.pk)
    if licencia.estado == Licencia.Estado.APROBADA:
        return licencia
    taller = Establecimiento.objects.select_for_update().get(pk=licencia.establecimiento_id)
    ahora = timezone.now()
    inicio = max(ahora, taller.licencia_hasta) if taller.licencia_hasta else ahora

    licencia.estado = Licencia.Estado.APROBADA
    licencia.fecha_inicio = inicio
    licencia.fecha_fin = inicio + timedelta(days=licencia.plan.dias)
    licencia.aprobada_por = usuario
    licencia.aprobada_en = ahora
    licencia.save()

    taller.licencia_hasta = licencia.fecha_fin
    taller.save(update_fields=['licencia_hasta'])
    return licencia


def rechazar(licencia, usuario, motivo=''):
    if licencia.estado != Licencia.Estado.PENDIENTE:
        raise ValidationError('Solo se pueden rechazar solicitudes pendientes.')
    licencia.estado = Licencia.Estado.RECHAZADA
    if motivo:
        licencia.notas = f'{licencia.notas}\n{motivo}'.strip()
    licencia.save(update_fields=['estado', 'notas'])
    return licencia
