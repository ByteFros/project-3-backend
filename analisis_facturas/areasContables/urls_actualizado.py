from django.urls import path

from .views.sumViews import (
    SumatoriasBOEView, 
    TotalActivoView, 
    TotalPasivoYPatrimonioView, 
    EstadoResultadosView,
    EstadoResultadosCorregidoView,  # NUEVA
    ResumenResultadosView           # NUEVA
)
from .views.views import FacturaUploadView, ResumenMensualView, LineasFacturaListView, AnalisisDuplicadosView

urlpatterns = [
    path('facturas/upload/', FacturaUploadView.as_view(), name='factura-upload'),
    #ejemplo de uso  GET /areasContables/resumen/?año=2024&mes=1
    path("resumen/", ResumenMensualView.as_view(), name="resumen-mensual"),
    #ejemplo de uso  GET /areasContables/lineas/?año=2024&mes=1
    path("lineas/", LineasFacturaListView.as_view(), name="lineas-factura"),
    #ejemplo de uso  GET /areasContables/analisis-duplicados/
    path('analisis-duplicados/', AnalisisDuplicadosView.as_view(), name='analisis-duplicados'),
    #ejemplo de uso  GET /areasContables/sumatorias-boe/
    path('sumatorias-boe/', SumatoriasBOEView.as_view(), name='sumatorias-boe'),
    #ejemplo de uso  GET /areasContables/total-activo/
    path('total-activo/', TotalActivoView.as_view(), name='total-activo'),

    path('total-patrimonio-pasivo/', TotalPasivoYPatrimonioView.as_view(), name='total-pasivo'),

    # VISTA ORIGINAL
    path("estado-resultados/", EstadoResultadosView.as_view(), name="estado-resultados"),
    
 ]
