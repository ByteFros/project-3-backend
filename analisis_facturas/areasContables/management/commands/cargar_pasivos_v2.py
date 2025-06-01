from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga Pasivos (No Corriente + Corriente) con estructura exacta del BOE'

    def handle(self, *args, **options):
        # Crear sección C con nomenclatura BOE
        seccion_c, _ = SeccionContable.objects.get_or_create(
            letra="C",
            defaults={"nombre": "C) PATRIMONIO NETO Y PASIVO"}
        )

        estructura = [
            # B) PASIVO NO CORRIENTE
            ("B) PASIVO NO CORRIENTE - I. Provisiones a largo plazo", "PROVL", "Obligaciones estimadas a largo plazo", [
                ("1. Obligaciones por prestaciones a largo plazo al personal", "140", ""),
                ("2. Actuaciones medioambientales", "145", ""),
                ("3. Provisiones por reestructuración", "146", ""),
                ("4. Otras provisiones", "141,142,143,147", ""),
            ]),

            ("B) PASIVO NO CORRIENTE - II. Deudas a largo plazo", "DEULP", "Pasivos financieros con vencimiento largo", [
                ("1. Obligaciones y otros valores negociables", "177,178,179", ""),
                ("2. Deudas con entidades de crédito", "1605,170", ""),
                ("3. Acreedores por arrendamiento financiero", "1625,174", ""),
                ("4. Derivados", "176", ""),
                ("5. Otros pasivos financieros", "1615,1635,171,172,173,175,180,185,189", ""),
            ]),

            ("B) PASIVO NO CORRIENTE - III. Deudas con empresas del grupo y asociadas a largo plazo", "DEUGRU", "Préstamos y obligaciones con el grupo", [
                ("Deudas con empresas del grupo y asociadas a largo plazo", "1603,1604,1613,1614,1623,1624,1633,1634", ""),
            ]),

            ("B) PASIVO NO CORRIENTE - IV. Pasivos por impuesto diferido", "IMPDIFF", "Impuestos que se devengarán en el futuro", [
                ("Pasivos por impuesto diferido", "479", ""),
            ]),

            ("B) PASIVO NO CORRIENTE - V. Periodificaciones a largo plazo", "PERLP", "Ajustes de ingresos/gastos a largo plazo", [
                ("Periodificaciones a largo plazo", "181", ""),
            ]),

            # C) PASIVO CORRIENTE
            ("C) PASIVO CORRIENTE - I. Pasivos vinculados con activos no corrientes mantenidos para la venta", "PVANC", "Pasivos vinculados a activos clasificados para la venta", [
                ("Pasivos vinculados con activos no corrientes mantenidos para la venta", "585,586,587,588,589", ""),
            ]),

            ("C) PASIVO CORRIENTE - II. Provisiones a corto plazo", "PROVC", "Obligaciones estimadas con vencimiento próximo", [
                ("Provisiones a corto plazo", "499,529", ""),
            ]),

            ("C) PASIVO CORRIENTE - III. Deudas a corto plazo", "DEUC", "Obligaciones financieras de corto plazo", [
                ("1. Obligaciones y otros valores negociables", "500,501,505,506", ""),
                ("2. Deudas con entidades de crédito", "5105,520,527", ""),
                ("3. Acreedores por arrendamiento financiero", "5125,524", ""),
                ("4. Derivados", "5595,5598", ""),
                ("5. Otros pasivos financieros", "509,5115,5135,5145,521,522,523,525,526,528,551,5525,555,5565,5566,560,561,569,194", "1034,1044,190,192"),
            ]),

            ("C) PASIVO CORRIENTE - IV. Deudas con empresas del grupo y asociadas a corto plazo", "DEUGC", "Préstamos y obligaciones intra grupo con vencimiento próximo", [
                ("Deudas con empresas del grupo y asociadas a corto plazo", "5103,5104,5113,5114,5123,5124,5133,5134,5143,5144,5523,5524,5563,5564", ""),
            ]),

            ("C) PASIVO CORRIENTE - V. Acreedores comerciales y otras cuentas a pagar", "ACREED", "Deudas con proveedores, empleados y Hacienda", [
                ("1. Proveedores", "400,401,405", "406"),
                ("2. Proveedores, empresas del grupo y asociadas", "403,404", ""),
                ("3. Acreedores varios", "41", ""),
                ("4. Personal (remuneraciones pendientes de pago)", "465,466", ""),
                ("5. Pasivos por impuesto corriente", "4752", ""),
                ("6. Otras deudas con las Administraciones Públicas", "4750,4751,4758,476,477", ""),
                ("7. Anticipos de clientes", "438", ""),
            ]),

            ("C) PASIVO CORRIENTE - VI. Periodificaciones a corto plazo", "PERC", "Gastos e ingresos contabilizados en ejercicios posteriores", [
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

        self.stdout.write(self.style.SUCCESS("✅ Carga de PASIVOS (estructura BOE exacta) completada correctamente."))
