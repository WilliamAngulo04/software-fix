from django.urls import path

from . import views

urlpatterns = [
    path('', views.UsuarioListView.as_view(), name='usuario_list'),
    path('nuevo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('mi-taller/', views.EstablecimientoUpdateView.as_view(), name='establecimiento_update'),
]
