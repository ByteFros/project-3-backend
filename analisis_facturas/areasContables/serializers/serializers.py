from rest_framework import serializers
from ..models import LineaFactura

class LineaFacturaSerializer(serializers.ModelSerializer):
    subarea = serializers.StringRelatedField()  # Muestra el nombre de la subárea
    area = serializers.SerializerMethodField()  # Muestra también el nombre del área

    class Meta:
        model = LineaFactura
        fields = [
            "id",
            "fecha",
            "asiento",
            "cuenta",
            "nombre",
            "concepto",
            "debe",
            "haber",
            "subarea",
            "area",
        ]

    def get_area(self, obj):
        return obj.subarea.area.nombre if obj.subarea and obj.subarea.area else None
