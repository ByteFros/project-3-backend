from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models.estado_resultado import EstadoResultado
from ..serializers.estado_resultado_serializer import EstadoResultadosSerializer, \
    EstadoResultadoSerializer


class CalcularEstadoResultadosView(APIView):
    def post(self, request):
        data = request.data

        def calcular_resultado(validated_data):
            ingresos = float(validated_data['ingresos'])
            costo = float(validated_data['costo_ventas'])
            gastos_op = float(validated_data['gastos_operativos'])
            otros_ingresos = float(validated_data['otros_ingresos'])
            otros_gastos = float(validated_data['otros_gastos'])

            ganancia_bruta = ingresos - costo
            ganancia_operativa = ganancia_bruta - gastos_op
            resultado_neto = ganancia_operativa + otros_ingresos - otros_gastos

            margen_bruto = (ganancia_bruta / ingresos) * 100 if ingresos else 0
            margen_operativo = (ganancia_operativa / ingresos) * 100 if ingresos else 0
            margen_neto = (resultado_neto / ingresos) * 100 if ingresos else 0

            # Clasificación por estado financiero
            estado = "en ganancias" if resultado_neto > 0 else "en pérdidas"

            # Evaluación de riesgo
            if margen_neto >= 15:
                riesgo = "saludable"
            elif margen_neto >= 5:
                riesgo = "moderado"
            else:
                riesgo = "alto"
            # Guardar en la base de datos
            if not EstadoResultado.objects.filter(id_unico=validated_data['id_unico']).exists():
                EstadoResultado.objects.create(
                    id_unico=validated_data['id_unico'],
                    cliente=validated_data['cliente'],
                    ingresos=ingresos,
                    costo_ventas=costo,
                    gastos_operativos=gastos_op,
                    otros_ingresos=otros_ingresos,
                    otros_gastos=otros_gastos,
                    ganancia_bruta=ganancia_bruta,
                    ganancia_operativa=ganancia_operativa,
                    resultado_neto=resultado_neto,
                    margen_bruto=round(margen_bruto, 2),
                    margen_operativo=round(margen_operativo, 2),
                    margen_neto=round(margen_neto, 2),
                    estado=estado,
                    riesgo=riesgo
                )

            return {
                "cliente": validated_data['cliente'],
                "id_unico": validated_data['id_unico'],
                "ingresos": ingresos,
                "costo_ventas": costo,
                "gastos_operativos": gastos_op,
                "otros_ingresos": otros_ingresos,
                "otros_gastos": otros_gastos,
                "ganancia_bruta": ganancia_bruta,
                "ganancia_operativa": ganancia_operativa,
                "resultado_neto": resultado_neto,
                "margen_bruto": round(margen_bruto, 2),
                "margen_operativo": round(margen_operativo, 2),
                "margen_neto": round(margen_neto, 2),
                "estado": estado,
                "riesgo": riesgo
            }

        is_list = isinstance(data, list)
        serializer = EstadoResultadosSerializer(data=data, many=is_list)

        if serializer.is_valid():
            validados = serializer.validated_data
            if is_list:
                resultados = [calcular_resultado(item) for item in validados]
                return Response(resultados, status=200)
            else:
                return Response(calcular_resultado(validados), status=200)

        return Response(serializer.errors, status=400)

class EstadoResultadoListView(APIView):
    def get(self, request):
        estados = EstadoResultado.objects.all()
        serializer = EstadoResultadoSerializer(estados, many=True)
        return Response(serializer.data, status=200)

class EstadoResultadoDetailView(APIView):
    def put(self, request, id_unico):
        estado = get_object_or_404(EstadoResultado, id_unico=id_unico)
        serializer = EstadoResultadoSerializer(estado, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)

    def delete(self, request, id_unico):
        estado = get_object_or_404(EstadoResultado, id_unico=id_unico)
        estado.delete()
        return Response(status=204)