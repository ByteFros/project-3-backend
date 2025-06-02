from django.db import models

class SeccionContable(models.Model):
    nombre = models.CharField(max_length=100)
    letra = models.CharField(max_length=2, unique=True)


    def __str__(self):
        return f"{self.letra} - {self.nombre}"


class AreaContable(models.Model):
    seccion = models.ForeignKey('SeccionContable', on_delete=models.CASCADE, related_name='areas')
    nombre = models.CharField(max_length=255)
    abreviatura = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True)
    afirmaciones_afectadas = models.TextField(
        blank=True,
        default="",
        help_text="Lista de afirmaciones afectadas, separadas por coma"
    )

    def __str__(self):
        return f"{self.seccion.letra}.{self.abreviatura} - {self.nombre}"

class SubAreaContable(models.Model):
    area = models.ForeignKey('AreaContable', on_delete=models.CASCADE, related_name='subareas')
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)

    # Códigos como string separados por comas (para SQLite)
    codigos_positivos = models.CharField(max_length=255, help_text="Ej: '201,202'")
    codigos_negativos = models.CharField(max_length=255, blank=True, default="", help_text="Ej: '2811,2901'")

    def __str__(self):
        return f"{self.area.nombre} - {self.nombre}"

    def codigos_pos_list(self):
        return [int(c.strip()) for c in self.codigos_positivos.split(',') if c.strip().isdigit()]

    def codigos_neg_list(self):
        return [int(c.strip()) for c in self.codigos_negativos.split(',') if c.strip().isdigit()]

class LineaFactura(models.Model):
    subarea = models.ForeignKey('SubAreaContable', on_delete=models.SET_NULL, null=True, blank=True, related_name='lineas')

    fecha = models.DateField(null=True, blank=True)
    asiento = models.CharField(max_length=10, blank=True)
    cuenta = models.CharField(max_length=20)
    nombre = models.CharField(max_length=255, blank=True)
    concepto = models.TextField(blank=True)
    debe = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    haber = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Asiento {self.asiento} | Cuenta {self.cuenta} - {self.nombre}"
