from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga el Pasivo Corriente dentro de la Sección C: Patrimonio Neto y Pasivo'

    def handle(self, *args, **options):
        # Crear sección C si no existe
        seccion_c, _ = SeccionContable.objects.get_or_create(
            letra="C",
            defaults={"nombre": "PATRIMONIO NETO Y PASIVO"}
        )

        estructura = [
            ("Pasivos vinculados con activos no corrientes mantenidos para la venta", "PVANC", "Pasivos vinculados a activos clasificados para la venta", [
                ("Pasivos vinculados con activos no corrientes mantenidos para la venta", "585,586,587,588,589", ""),
            ]),

            ("Provisiones a corto plazo", "PROVC", "Obligaciones estimadas con vencimiento próximo", [
                ("Provisiones a corto plazo", "499,529", ""),
            ]),

            ("Deudas a corto plazo", "DEUC", "Obligaciones financieras de corto plazo", [
                ("Obligaciones y otros valores negociables", "500,501,505,506", ""),
                ("Entidades de crédito", "5105,520,527", ""),
                ("Arrendamiento financiero", "5125,524", ""),
                ("Derivados financieros", "5595,5598", ""),
                ("Otros pasivos financieros", "509,5115,5135,5145,521,522,523,525,526,528,551,5525,555,5565,5566,560,561,569,194", "1034,1044,190,192"),
            ]),

            ("Deudas con empresas del grupo y asociadas a corto plazo", "DEUGC", "Préstamos y obligaciones intra grupo con vencimiento próximo", [
                ("Deudas con empresas del grupo y asociadas a corto plazo", "5103,5104,5113,5114,5123,5124,5133,5134,5143,5144,5523,5524,5563,5564", ""),
            ]),

            ("Acreedores comerciales y otras cuentas a pagar", "ACREED", "Deudas con proveedores, empleados y Hacienda", [
                ("Proveedores", "400,401,405", "406"),
                ("Proveedores, empresas del grupo y asociadas", "403,404", ""),
                ("Acreedores varios", "41", ""),
                ("Personal (remuneraciones pendientes de pago)", "465,466", ""),
                ("Pasivos por impuesto corriente", "4752", ""),
                ("Otras deudas con las Administraciones Públicas", "4750,4751,4758,476,477", ""),
                ("Anticipos de clientes", "438", ""),
            ]),

            ("Periodificaciones a corto plazo", "PERC", "Gastos e ingresos contabilizados en ejercicios posteriores", [
                ("Periodificaciones a corto plazo", "485,568", ""),
            ]),
        ]

        for nombre, abrev, descripcion, subareas in estructura:
            area, created = AreaContable.objects.get_or_create(
                nombre=nombre,
                seccion=seccion_c,
                defaults={
                    "abreviatura": abrev,
                    "descripcion": descripcion
                }
            )

            if created:
                self.stdout.write(f"Área creada: {nombre}")
            else:
                self.stdout.write(f"Área ya existente: {nombre}")

            for sub_nombre, cod_pos, cod_neg in subareas:
                subarea, sub_created = SubAreaContable.objects.get_or_create(
                    area=area,
                    nombre=sub_nombre,
                    defaults={
                        "descripcion": "",
                        "codigos_positivos": cod_pos,
                        "codigos_negativos": cod_neg
                    }
                )

                if sub_created:
                    self.stdout.write(f"  Subárea creada: {sub_nombre}")
                else:
                    self.stdout.write(f"  Subárea ya existente: {sub_nombre}")

        self.stdout.write(self.style.SUCCESS("✅ Carga del Pasivo Corriente completada correctamente."))
