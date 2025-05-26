from rest_framework import serializers

from ..models.estado_resultado import EstadoResultado


class EstadoResultadosSerializer(serializers.Serializer):
    id_unico = serializers.CharField()
    cliente = serializers.CharField()
    ingresos = serializers.DecimalField(max_digits=12, decimal_places=2)
    costo_ventas = serializers.DecimalField(max_digits=12, decimal_places=2)
    gastos_operativos = serializers.DecimalField(max_digits=12, decimal_places=2)
    otros_ingresos = serializers.DecimalField(max_digits=12, decimal_places=2)
    otros_gastos = serializers.DecimalField(max_digits=12, decimal_places=2)


class EstadoResultadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstadoResultado
        fields = '__all__'