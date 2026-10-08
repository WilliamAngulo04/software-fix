from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from config.estilos import BootstrapMixin

from .models import Establecimiento, Usuario


class LoginForm(BootstrapMixin, AuthenticationForm):
    pass


class EstablecimientoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Establecimiento
        fields = ['nombre', 'nit', 'telefono', 'direccion']


class RegistroForm(BootstrapMixin, forms.Form):
    """Registro público: crea un taller nuevo y su usuario administrador."""

    taller = forms.CharField(label='Nombre del taller', max_length=120)
    telefono_taller = forms.CharField(label='Teléfono del taller', max_length=20, required=False)
    nombre = forms.CharField(label='Tu nombre', max_length=100)
    email = forms.EmailField(label='Email', max_length=100)
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    def clean_email(self):
        email = Usuario.objects.normalize_email(self.cleaned_data['email']).lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este email.')
        return email

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if p1 and p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(p1, Usuario(email=datos.get('email', ''), nombre=datos.get('nombre', '')))
                except forms.ValidationError as error:
                    self.add_error('password1', error)
        return datos


class UsuarioForm(BootstrapMixin, forms.ModelForm):
    """Crea o edita un usuario. La contraseña es obligatoria solo al crear."""

    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput, required=False)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput, required=False)

    class Meta:
        model = Usuario
        fields = ['nombre', 'email', 'rol', 'activo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['password1'].required = True
            self.fields['password2'].required = True
        else:
            self.fields['password1'].help_text = 'Déjala vacía para conservar la actual.'

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Las contraseñas no coinciden.')
            else:
                try:
                    validate_password(p1, self.instance)
                except forms.ValidationError as error:
                    self.add_error('password1', error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
        return usuario
