from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la SECCIÓN A: Activo No Corriente con áreas y subáreas contables según BOE'

    def handle(self, *args, **options):
        # Crear sección A
        seccion_a, _ = SeccionContable.objects.get_or_create(
            letra="A",
            defaults={"nombre": "ACTIVO NO CORRIENTE"}
        )

        estructura = [
            # (nombre_area, abreviatura, descripcion_area, subareas: [(nombre_sub, cod_pos, cod_neg)])

            ("Inmovilizado Intangible", "II", "Activos no materiales usados en la actividad empresarial", [
                ("Desarrollo", "201", "2801,2901"),
                ("Concesiones", "202", "2802,2902"),
                ("Patentes, licencias, marcas y similares", "203", "2803,2903"),
                ("Fondo de comercio", "204", "2804"),
                ("Aplicaciones informáticas", "206", "2806,2906"),
                ("Otro inmovilizado intangible", "205,209", "2805,2905"),
            ]),

            ("Inmovilizado Material", "IM", "Bienes físicos tangibles", [
                ("Terrenos y construcciones", "210,211", "2811,2910,2911"),
                ("Instalaciones técnicas y otros", "212,213,214,215,216,217,218,219",
                 "2812,2813,2814,2815,2816,2817,2818,2819,2912,2913,2914,2915,2916,2917,2918,2919"),
                ("Inmovilizado en curso y anticipos", "23", ""),
            ]),

            ("Inversiones Inmobiliarias", "INVIM", "Activos inmobiliarios para alquiler o plusvalía", [
                ("Terrenos", "220", "2920"),
                ("Construcciones", "221", "282,2921"),
            ]),

            ("Inversiones en empresas del grupo y asociadas (LP)", "INVGRU", "Participaciones financieras a largo plazo en empresas del grupo", [
                ("Instrumentos de patrimonio", "2403,2404", "2493,2494,293"),
                ("Créditos a empresas", "2423,2424", "2953,2954"),
                ("Valores representativos de deuda", "2413,2414", "2943,2944"),
                ("Derivados", "", ""),
                ("Otros activos financieros", "", ""),
            ]),

            ("Inversiones financieras a largo plazo", "INVFIN", "Activos financieros a largo plazo con terceros", [
                ("Instrumentos de patrimonio", "2405,250", "2495,259"),
                ("Créditos a terceros", "2425,252,253,254", "2955,298"),
                ("Valores representativos de deuda", "2415,251", "2945,297"),
                ("Derivados", "255", ""),
                ("Otros activos financieros", "258,26", ""),
            ]),

            ("Activos por impuesto diferido", "AID", "Créditos fiscales recuperables en el futuro", [
                ("Activos por impuesto diferido", "474", ""),
            ]),
        ]

        for nombre, abrev, descripcion, subareas in estructura:
            area, created = AreaContable.objects.get_or_create(
                nombre=nombre,
                seccion=seccion_a,
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa de la Sección A finalizada correctamente."))
