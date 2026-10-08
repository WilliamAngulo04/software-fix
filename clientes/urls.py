from django.urls import path

from . import views

urlpatterns = [
    path('', views.ClienteListView.as_view(), name='cliente_list'),
    path('nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('<int:pk>/', views.ClienteDetailView.as_view(), name='cliente_detail'),
    path('<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('<int:cliente_pk>/equipos/nuevo/', views.EquipoCreateView.as_view(), name='equipo_create'),
    path('equipos/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='equipo_update'),
]
