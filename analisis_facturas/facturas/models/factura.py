from django.db import models

class Factura(models.Model):
    factura_id_unico = models.CharField(max_length=100, unique=True)
    numero = models.CharField(max_length=50)
    cliente = models.CharField(max_length=100)
    fecha = models.DateField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    iva = models.DecimalField(max_digits=10, decimal_places=2)
    total_con_iva = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Factura {self.numero} - {self.cliente}"
