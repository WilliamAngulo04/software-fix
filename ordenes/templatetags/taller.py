from django import template
from django.utils.safestring import mark_safe

from clientes import patron

register = template.Library()

COLORES_ESTADO = {
    'recibido': 'secondary',
    'en_diagnostico': 'info',
    'esperando_aprobacion': 'warning',
    'en_reparacion': 'primary',
    'listo_entrega': 'success',
    'entregado': 'dark',
    'cancelado': 'danger',
}


@register.filter
def color_estado(estado):
    return COLORES_ESTADO.get(estado, 'secondary')


@register.filter
def dinero(valor):
    """Formatea un valor como $1.234.567 (sin decimales si son cero)."""
    if valor in (None, ''):
        return '$0'
    entero = int(valor)
    texto = f'{entero:,}'.replace(',', '.')
    decimales = int(round((valor - entero) * 100))
    return f'${texto},{decimales:02d}' if decimales else f'${texto}'


@register.filter
def patron_svg(valor, tamano=120):
    """Dibujo del patrón de desbloqueo guardado (ej. "14789")."""
    if not valor or not str(valor).isdigit():
        return ''
    return mark_safe(patron.svg(str(valor), int(tamano)))


@register.simple_tag(takes_context=True)
def url_con(context, **cambios):
    """Devuelve la query string actual con los parámetros indicados reemplazados (para paginar con filtros)."""
    params = context['request'].GET.copy()
    for clave, valor in cambios.items():
        params[clave] = valor
    return '?' + params.urlencode()
