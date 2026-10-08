"""
Patrón de desbloqueo de 3x3. Los puntos se numeran así:

    1 2 3
    4 5 6
    7 8 9

y el patrón se guarda como la secuencia de puntos en orden, ej. "14789" (una L).
"""
from django import forms
from django.utils.html import format_html, format_html_join

MINIMO_PUNTOS = 4


def coordenadas(punto):
    """Columna y fila (0-2) de un punto 1-9."""
    n = int(punto) - 1
    return n % 3, n // 3


def validar(valor):
    if not valor:
        return None
    if not valor.isdigit() or '0' in valor:
        raise forms.ValidationError('El patrón solo puede usar los puntos del 1 al 9.')
    if len(set(valor)) != len(valor):
        raise forms.ValidationError('El patrón no puede repetir puntos.')
    if len(valor) < MINIMO_PUNTOS:
        raise forms.ValidationError(f'El patrón debe unir al menos {MINIMO_PUNTOS} puntos.')
    return valor


class PatronInput(forms.TextInput):
    """Cuadrícula de 3x3 para dibujar el patrón (la lógica está en static/js/patron.js)."""

    def render(self, name, value, attrs=None, renderer=None):
        attrs = self.build_attrs(self.attrs, attrs)
        id_input = attrs.get('id', f'id_{name}')
        puntos = format_html_join(
            '', '<circle class="patron-punto" data-punto="{}" cx="{}" cy="{}" r="14"></circle>',
            ((i, 50 + 100 * ((i - 1) % 3), 50 + 100 * ((i - 1) // 3)) for i in range(1, 10)),
        )
        return format_html(
            '<div class="patron-editor" data-input="{id}">'
            '<input type="hidden" name="{name}" id="{id}" value="{valor}">'
            '<svg viewBox="0 0 300 300" class="patron-lienzo" role="img" aria-label="Dibuja el patrón">'
            '<polyline class="patron-trazo" points=""></polyline>{puntos}</svg>'
            '<div class="d-flex justify-content-between align-items-center mt-1">'
            '<small class="patron-texto text-body-secondary">Dibuja el patrón uniendo los puntos</small>'
            '<button type="button" class="btn btn-sm btn-outline-secondary patron-limpiar">Borrar</button>'
            '</div></div>',
            id=id_input, name=name, valor=value or '', puntos=puntos,
        )


def svg(valor, tamano=120):
    """Dibujo del patrón (solo lectura) con el inicio marcado y el orden numerado."""
    if not valor:
        return ''
    centros = {p: (50 + 100 * coordenadas(p)[0], 50 + 100 * coordenadas(p)[1]) for p in valor}
    trazo = ' '.join(f'{x},{y}' for x, y in (centros[p] for p in valor))
    partes = [f'<polyline points="{trazo}" fill="none" stroke="#0d6efd" stroke-width="10" '
              'stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>']
    for i in range(1, 10):
        x, y = 50 + 100 * ((i - 1) % 3), 50 + 100 * ((i - 1) // 3)
        usado = str(i) in valor
        partes.append(f'<circle cx="{x}" cy="{y}" r="{18 if usado else 9}" '
                      f'fill="{"#0d6efd" if usado else "#adb5bd"}"/>')
    inicio = centros[valor[0]]
    partes.append(f'<circle cx="{inicio[0]}" cy="{inicio[1]}" r="27" fill="none" stroke="#198754" stroke-width="7"/>')
    for orden, p in enumerate(valor, 1):
        x, y = centros[p]
        partes.append(f'<text x="{x}" y="{y + 8}" text-anchor="middle" font-size="22" '
                      f'font-weight="bold" fill="#fff" font-family="sans-serif">{orden}</text>')
    return (f'<svg viewBox="0 0 300 300" width="{tamano}" height="{tamano}" role="img" '
            f'aria-label="Patrón {valor}" style="background:#f8f9fa;border-radius:8px">{"".join(partes)}</svg>')
