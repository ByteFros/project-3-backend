from django.db import models

class EstadoResultado(models.Model):
    id_unico = models.CharField(max_length=100, unique=True)
    cliente = models.CharField(max_length=100)
    ingresos = models.DecimalField(max_digits=12, decimal_places=2)
    costo_ventas = models.DecimalField(max_digits=12, decimal_places=2)
    gastos_operativos = models.DecimalField(max_digits=12, decimal_places=2)
    otros_ingresos = models.DecimalField(max_digits=12, decimal_places=2)
    otros_gastos = models.DecimalField(max_digits=12, decimal_places=2)

    ganancia_bruta = models.DecimalField(max_digits=12, decimal_places=2)
    ganancia_operativa = models.DecimalField(max_digits=12, decimal_places=2)
    resultado_neto = models.DecimalField(max_digits=12, decimal_places=2)

    margen_bruto = models.DecimalField(max_digits=5, decimal_places=2)
    margen_operativo = models.DecimalField(max_digits=5, decimal_places=2)
    margen_neto = models.DecimalField(max_digits=5, decimal_places=2)

    estado = models.CharField(max_length=20)
    riesgo = models.CharField(max_length=20)

    def __str__(self):
        return f"{self.cliente} - {self.id_unico}"