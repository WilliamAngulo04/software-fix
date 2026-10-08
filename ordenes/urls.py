from django.urls import path

from . import views

urlpatterns = [
    path('', views.OrdenListView.as_view(), name='orden_list'),
    path('nueva/', views.OrdenCreateView.as_view(), name='orden_create'),
    path('<int:pk>/', views.OrdenDetailView.as_view(), name='orden_detail'),
    path('<int:pk>/actualizar/', views.OrdenActualizarView.as_view(), name='orden_actualizar'),
    path('<int:pk>/comprobante/', views.OrdenComprobanteView.as_view(), name='orden_comprobante'),
    path('<int:pk>/evidencias/', views.EvidenciaCreateView.as_view(), name='evidencia_create'),
    path('<int:pk>/repuestos/', views.RepuestoAgregarView.as_view(), name='repuesto_agregar'),
    path('<int:pk>/repuestos/<int:detalle_pk>/quitar/', views.RepuestoQuitarView.as_view(), name='repuesto_quitar'),
]
