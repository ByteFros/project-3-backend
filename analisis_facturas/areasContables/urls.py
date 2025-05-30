from django.urls import path
from .views.views import FacturaUploadView, ResumenMensualView, LineasFacturaListView, AnalisisDuplicadosView

urlpatterns = [
    path('facturas/upload/', FacturaUploadView.as_view(), name='factura-upload'),
    #ejemplo de uso  GET /areasContables/resumen/?año=2024&mes=1
    path("resumen/", ResumenMensualView.as_view(), name="resumen-mensual"),
    #ejemplo de uso  GET /areasContables/lineas/?año=2024&mes=1
    path("lineas/", LineasFacturaListView.as_view(), name="lineas-factura"),
    #ejemplo de uso  GET /areasContables/analisis-duplicados/
    path('analisis-duplicados/', AnalisisDuplicadosView.as_view(), name='analisis-duplicados')

]
