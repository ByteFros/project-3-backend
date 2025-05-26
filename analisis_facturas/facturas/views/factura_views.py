import pandas as pd
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from ..models.factura import Factura
from ..serializers.factura_serializer import FacturaSerializer, FacturaInputSerializer


class UploadFacturaView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, format=None):
        file_obj = request.data['file']
        df = pd.read_excel(file_obj)

        procesadas = []
        duplicadas = []

        for _, row in df.iterrows():
            factura_id = str(row['id_unico'])
            if not Factura.objects.filter(factura_id_unico=factura_id).exists():
                total = float(row['subtotal'])
                iva = total * 0.21
                total_con_iva = total + iva

                Factura.objects.create(
                    factura_id_unico=factura_id,
                    numero=row['numero'],
                    cliente=row['cliente'],
                    fecha=pd.to_datetime(row['fecha']).date(),
                    total=total,
                    iva=iva,
                    total_con_iva=total_con_iva
                )
                procesadas.append(factura_id)
            else:
                duplicadas.append(factura_id)

        return JsonResponse({
            'procesadas': procesadas,
            'duplicadas': duplicadas
        })


class FacturasProcesadasView(ListAPIView):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer


class FacturaDetalleView(RetrieveAPIView):
    queryset = Factura.objects.all()
    serializer_class = FacturaSerializer
    lookup_field = 'factura_id_unico'


class RecibirFacturaJSONView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data

        def procesar_factura(validated_data):
            subtotal = float(validated_data['subtotal'])
            iva = round(subtotal * 0.21, 2)
            total_con_iva = round(subtotal + iva, 2)

            return {
                **validated_data,
                'iva': iva,
                'total_con_iva': total_con_iva
            }

        # Procesar lista de facturas
        if isinstance(data, list):
            serializer = FacturaInputSerializer(data=data, many=True)
        else:
            serializer = FacturaInputSerializer(data=data)

        if serializer.is_valid():
            datos_validos = serializer.validated_data
            if isinstance(datos_validos, list):
                resultado = [procesar_factura(f) for f in datos_validos]
            else:
                resultado = procesar_factura(datos_validos)
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
