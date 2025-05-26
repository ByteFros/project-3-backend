from django.urls import path

from .views.estado_resultado_views import CalcularEstadoResultadosView, \
    EstadoResultadoListView, EstadoResultadoDetailView
from .views.factura_views import UploadFacturaView, FacturasProcesadasView, \
    FacturaDetalleView, RecibirFacturaJSONView

urlpatterns = [
    path('subir/', UploadFacturaView.as_view()),
    path('listar/', FacturasProcesadasView.as_view()),
    path('detalle/<str:factura_id_unico>/', FacturaDetalleView.as_view()),
    path('factura_json/', RecibirFacturaJSONView.as_view()),
    path('estado_resultados/', CalcularEstadoResultadosView.as_view()),
    path('estado_resultados2/', EstadoResultadoListView.as_view(), name='listar_estados'),
    path('estado_resultados/<str:id_unico>/', EstadoResultadoDetailView.as_view(), name='detalle_estado'),
]
