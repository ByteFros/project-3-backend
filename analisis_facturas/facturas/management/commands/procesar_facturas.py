import pandas as pd
from django.core.management.base import BaseCommand

from analisis_facturas.facturas.models.factura import Factura


class Command(BaseCommand):
    help = "Procesa facturas desde archivo Excel"

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Ruta del archivo Excel')

    def handle(self, *args, **kwargs):
        path = kwargs['path']
        df = pd.read_excel(path)

        for _, row in df.iterrows():
            factura_id = str(row['id_unico'])  # columna en tu Excel
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
                self.stdout.write(self.style.SUCCESS(f"Factura {factura_id} procesada"))
            else:
                self.stdout.write(self.style.WARNING(f"Factura {factura_id} ya existe"))
