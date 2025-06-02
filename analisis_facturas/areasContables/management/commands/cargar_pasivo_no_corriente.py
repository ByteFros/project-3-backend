from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga el Pasivo No Corriente dentro de la Sección C: Patrimonio Neto y Pasivo'

    def handle(self, *args, **options):
        # Crear sección C si no existe
        seccion_d, _ = SeccionContable.objects.get_or_create(
            letra="D",
            defaults={"nombre": "D) PASIVO NO CORRIENTE"}
        )

        estructura = [
            ("Provisiones a largo plazo", "PROVL", "Obligaciones estimadas a largo plazo", [
                ("Prestaciones a largo plazo al personal", "140", ""),
                ("Actuaciones medioambientales", "145", ""),
                ("Provisiones por reestructuración", "146", ""),
                ("Otras provisiones", "141,142,143,147", ""),
            ]),

            ("Deudas a largo plazo", "DEULP", "Pasivos financieros con vencimiento largo", [
                ("Obligaciones y valores negociables", "177,178,179", ""),
                ("Entidades de crédito", "1605,170", ""),
                ("Arrendamiento financiero", "1625,174", ""),
                ("Derivados financieros", "176", ""),
                ("Otros pasivos financieros", "1615,1635,171,172,173,175,180,185,189", ""),
            ]),

            ("Deudas con empresas del grupo y asociadas", "DEUGRU", "Préstamos y obligaciones con el grupo", [
                ("Deudas largo plazo con el grupo", "1603,1604,1613,1614,1623,1624,1633,1634", ""),
            ]),

            ("Pasivos por impuesto diferido", "IMPDIFF", "Impuestos que se devengarán en el futuro", [
                ("Impuesto diferido", "479", ""),
            ]),

            ("Periodificaciones a largo plazo", "PERLP", "Ajustes de ingresos/gastos a largo plazo", [
                ("Periodificaciones a largo plazo", "181", ""),
            ]),
        ]

        for nombre, abrev, descripcion, subareas in estructura:
            area, created = AreaContable.objects.get_or_create(
                nombre=nombre,
                seccion=seccion_d,
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

        self.stdout.write(self.style.SUCCESS("✅ Carga del Pasivo No Corriente completada correctamente."))
