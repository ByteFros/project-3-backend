from django.urls import path

from .views.sumViews import SumatoriasBOEView, TotalActivoView, TotalPasivoYPatrimonioView, \
    EstadoResultadosCorregidoView, IngresosGastosReconocidosView, TotalActivoCodigosView
from .views.views import FacturaUploadView, ResumenMensualView, AnalisisDuplicadosView, \
    LineasFacturaSampleListView

urlpatterns = [
    path('facturas/upload/', FacturaUploadView.as_view(), name='factura-upload'),
    #ejemplo de uso  GET /areasContables/resumen/?año=2024&mes=1
    path("resumen/", ResumenMensualView.as_view(), name="resumen-mensual"),
    #ejemplo de uso  GET /areasContables/lineas/?año=2024&mes=1
    path("lineas/", LineasFacturaSampleListView.as_view(), name="lineas-factura"),
    #ejemplo de uso  GET /areasContables/analisis-duplicados/
    path('analisis-duplicados/', AnalisisDuplicadosView.as_view(), name='analisis-duplicados'),
    #ejemplo de uso  GET /areasContables/sumatorias-boe/
    path('sumatorias-boe/', SumatoriasBOEView.as_view(), name='sumatorias-boe'),
    #ejemplo de uso  GET /areasContables/total-activo/
    path('total-activo/', TotalActivoView.as_view(), name='total-activo'),
    path('total-activo2/', TotalActivoCodigosView.as_view(), name='total_activo_2'),

    path('total-patrimonio/', TotalPasivoYPatrimonioView.as_view(), name='total-pasivo'),
    # NUEVAS VISTAS PARA PROBAR
    path('ganancias/', EstadoResultadosCorregidoView.as_view(), name='estado-resultados'),
    path('ingresos-gastos-reconocidos/', IngresosGastosReconocidosView.as_view(),
         name='ingresos_gastos_reconocidos'),

]
"""TODO  hay que ajustar la carga y si es posible migrar la informacion a postgres, ademas ajustar la carga de scripts con datos para que funcione la base de datos"""