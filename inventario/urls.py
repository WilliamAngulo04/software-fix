from django.urls import path

from . import views

urlpatterns = [
    path('', views.ProductoListView.as_view(), name='producto_list'),
    path('nuevo/', views.ProductoCreateView.as_view(), name='producto_create'),
    path('<int:pk>/editar/', views.ProductoUpdateView.as_view(), name='producto_update'),
]
