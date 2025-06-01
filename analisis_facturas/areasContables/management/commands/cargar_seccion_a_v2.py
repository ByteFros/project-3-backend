from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la SECCIÓN A: Activo No Corriente con nomenclatura exacta del BOE'

    def handle(self, *args, **options):
        # Crear sección A con nomenclatura BOE
        seccion_a, _ = SeccionContable.objects.get_or_create(
            letra="A",
            defaults={"nombre": "A) ACTIVO NO CORRIENTE"}
        )

        estructura = [
            ("I. Inmovilizado intangible", "II", "Activos no materiales usados en la actividad empresarial", [
                ("1. Desarrollo", "201", "2801,2901"),
                ("2. Concesiones", "202", "2802,2902"),
                ("3. Patentes, licencias, marcas y similares", "203", "2803,2903"),
                ("4. Fondo de comercio", "204", "2804"),
                ("5. Aplicaciones informáticas", "206", "2806,2906"),
                ("6. Otro inmovilizado intangible", "205,209", "2805,2905"),
            ]),

            ("II. Inmovilizado material", "IM", "Bienes físicos tangibles", [
                ("1. Terrenos y construcciones", "210,211", "2811,2910,2911"),
                ("2. Instalaciones técnicas, y otro inmovilizado material", "212,213,214,215,216,217,218,219",
                 "2812,2813,2814,2815,2816,2817,2818,2819,2912,2913,2914,2915,2916,2917,2918,2919"),
                ("3. Inmovilizado en curso y anticipos", "23", ""),
            ]),

            ("III. Inversiones inmobiliarias", "INVIM", "Activos inmobiliarios para alquiler o plusvalía", [
                ("1. Terrenos", "220", "2920"),
                ("2. Construcciones", "221", "282,2921"),
            ]),

            ("IV. Inversiones en empresas del grupo y asociadas a largo plazo", "INVGRU", "Participaciones financieras a largo plazo en empresas del grupo", [
                ("1. Instrumentos de patrimonio", "2403,2404", "2493,2494,293"),
                ("2. Créditos a empresas", "2423,2424", "2953,2954"),
                ("3. Valores representativos de deuda", "2413,2414", "2943,2944"),
                ("4. Derivados", "", ""),
                ("5. Otros activos financieros", "", ""),
            ]),

            ("V. Inversiones financieras a largo plazo", "INVFIN", "Activos financieros a largo plazo con terceros", [
                ("1. Instrumentos de patrimonio", "2405,250", "2495,259"),
                ("2. Créditos a terceros", "2425,252,253,254", "2955,298"),
                ("3. Valores representativos de deuda", "2415,251", "2945,297"),
                ("4. Derivados", "255", ""),
                ("5. Otros activos financieros", "258,26", ""),
            ]),

            ("VI. Activos por impuesto diferido", "AID", "Créditos fiscales recuperables en el futuro", [
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa de la Sección A (nomenclatura BOE) finalizada correctamente."))
