from rest_framework import serializers

from ..models.factura import Factura


class FacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Factura
        fields = '__all__'

class FacturaInputSerializer(serializers.Serializer):
    id_unico = serializers.CharField(max_length=100)
    numero = serializers.CharField(max_length=50)
    cliente = serializers.CharField(max_length=100)
    fecha = serializers.DateField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
