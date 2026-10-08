from django.urls import path

from . import views

urlpatterns = [
    path('planes/', views.PlanesView.as_view(), name='planes'),
    path('licencia/', views.MiLicenciaView.as_view(), name='mi_licencia'),
]
