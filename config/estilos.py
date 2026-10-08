from django import forms

TEXTO_VACIO = 'Selecciona una opción'


class BootstrapMixin:
    """Añade las clases CSS de Bootstrap a todos los campos y pone en español las opciones vacías."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, forms.CheckboxInput):
                clase = 'form-check-input'
            elif isinstance(widget, forms.RadioSelect):
                clase = 'form-check-input'
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {clase}".strip()

            if isinstance(widget, forms.Textarea) and widget.attrs.get('rows') in (None, '10', 10):
                widget.attrs['rows'] = 3

            # Opción vacía de las listas desplegables.
            if isinstance(campo, forms.ModelChoiceField):
                if campo.empty_label is not None and campo.empty_label.startswith(('-', '—')):
                    campo.empty_label = TEXTO_VACIO
            elif isinstance(campo, forms.ChoiceField) and not isinstance(widget, forms.RadioSelect):
                opciones = list(campo.choices)
                if opciones and opciones[0][0] == '':
                    campo.choices = [('', TEXTO_VACIO)] + opciones[1:]


class FechaHoraInput(forms.DateTimeInput):
    input_type = 'datetime-local'

    def __init__(self, **kwargs):
        super().__init__(format='%Y-%m-%dT%H:%M', **kwargs)
