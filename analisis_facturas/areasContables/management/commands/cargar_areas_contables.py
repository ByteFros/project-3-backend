from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable

class Command(BaseCommand):
    help = 'Carga jerárquica de secciones, áreas y subáreas contables según BOE'

    def handle(self, *args, **options):
        SECCIONES = {
            "A": "ACTIVO NO CORRIENTE",
            "B": "ACTIVO CORRIENTE",
            "C": "PATRIMONIO NETO Y PASIVO",
            "D": "CUENTA DE RESULTADOS"
        }

        estructura = [
            ("A", "Inmovilizado Intangible", "II", "Activos no materiales usados en la actividad empresarial", [
                ("Desarrollo", "201", "2801,2901"),
                ("Concesiones", "202", "2802,2902"),
                ("Patentes, licencias, marcas y similares", "203", "2803,2903"),
                ("Fondo de comercio", "204", "2804"),
                ("Aplicaciones informáticas", "206", "2806,2906"),
                ("Otro inmovilizado intangible", "205,209", "2805,2905"),
            ]),
            ("A", "Inmovilizado Material", "IM", "Bienes físicos tangibles", [
                ("Terrenos y construcciones", "210,211", "2811,2910,2911"),
                ("Instalaciones técnicas y otros", "212,213,214,215,216,217,218,219", "2812,2813,2814,2815,2816,2817,2818,2819,2912,2913,2914,2915,2916,2917,2918,2919"),
                ("Inmovilizado en curso y anticipos", "23", ""),
            ]),
            ("A", "Inversiones Inmobiliarias", "INVIM", "Activos inmobiliarios para alquiler o plusvalía", [
                ("Terrenos", "220", "2920"),
                ("Construcciones", "221", "282,2921"),
            ]),
            ("A", "Inversiones en empresas del grupo y asociadas (LP)", "INVGRU", "Participaciones financieras a largo plazo", [
                ("Instrumentos de patrimonio", "2403,2404", "2493,2494,293"),
                ("Créditos a empresas", "2423,2424", "2953,2954"),
                ("Valores representativos de deuda", "2413,2414", "2943,2944"),
                ("Otros activos financieros", "", ""),
            ]),
            ("A", "Inversiones financieras a largo plazo", "INVFIN", "Activos financieros con terceros", [
                ("Instrumentos de patrimonio", "2405,250", "2495,259"),
                ("Créditos a terceros", "2425,252,253,254", "2955,298"),
                ("Valores representativos de deuda", "2415,251", "2945,297"),
                ("Otros activos financieros", "255,258,26", ""),
                ("Fianzas constituidas a largo plazo", "260", ""),
            ]),
            ("A", "Activos por impuesto diferido", "AID", "Créditos fiscales futuros", [
                ("Activos por impuesto diferido", "474", ""),
                ("Deducciones y bonificaciones pendientes", "4742", ""),
                ("Créditos por pérdidas a compensar", "4745", ""),
            ]),
            ("C", "Patrimonio Neto", "PN", "Fondos propios y resultados acumulados", [
                ("Capital", "100,101,102", ""),
                ("Reservas", "110,112,113,114,115", ""),
                ("Resultados de ejercicios anteriores", "120,121", ""),
                ("Otras aportaciones y resultados", "118,129", ""),
                ("Subvenciones y donaciones", "130", ""),
            ]),
            ("C", "Pasivo No Corriente", "PNC", "Obligaciones y deudas a largo plazo", [
                ("Deudas a largo plazo", "170,1635", ""),
            ]),
            ("B", "Activo Corriente", "AC", "Bienes y derechos a corto plazo", [
                ("Clientes", "430,434,436", ""),
                ("Tesorería", "570,572", ""),
                ("Anticipos y otros créditos", "407,4708,4709,472", ""),
                ("Entidades financieras y bancos", "520,521", ""),
            ]),
            ("C", "Pasivo Corriente", "PC", "Deudas y obligaciones a corto plazo", [
                ("Proveedores y acreedores", "400,404,407,410", ""),
                ("Administraciones públicas", "4750,4751,4758,476,477,479", ""),
                ("Ajustes fiscales y provisiones", "465,480,485,490", ""),
                ("Proveedores - facturas pendientes", "4009", ""),
            ]),
            ("D", "Ingresos y Gastos", "IG", "Operaciones de explotación e ingresos diversos", [
                ("Ingresos", "703,704,705,730", ""),
                ("Gastos", "623,625,626,629,640,649", ""),
            ]),
            ("D", "Gastos", "GAST", "Gastos sociales y financieros", [
                ("Seguridad Social y cargas sociales", "621,642", ""),
                ("Intereses y diferencias de cambio", "662,668", ""),
                ("Trabajos realizados por otras empresas", "607", ""),
                ("Publicidad y relaciones públicas", "627", ""),
            ]),
            ("D", "Ingresos", "ING", "Ingresos varios y extraordinarios", [
                ("Ingresos extraordinarios", "778", ""),
                ("Diferencias positivas de cambio", "768", ""),
            ]),
            ("D", "Amortizaciones", "AMORT", "Amortizaciones del inmovilizado", [
                ("Amortización inmovilizado intangible", "680", ""),
                ("Amortización inmovilizado material", "681", ""),
            ]),
        ]

        for letra, nombre_area, abrev, descripcion, subareas in estructura:
            seccion, _ = SeccionContable.objects.get_or_create(
                letra=letra,
                defaults={"nombre": SECCIONES.get(letra, "OTRA")}
            )

            area, created = AreaContable.objects.get_or_create(
                nombre=nombre_area,
                seccion=seccion,
                defaults={
                    "abreviatura": abrev,
                    "descripcion": descripcion
                }
            )

            if created:
                self.stdout.write(f"Área creada: {nombre_area}")
            else:
                self.stdout.write(f"Área ya existía: {nombre_area}")

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

        total_areas = AreaContable.objects.count()
        total_subareas = SubAreaContable.objects.count()
        self.stdout.write(self.style.SUCCESS(f"✔ Total de áreas: {total_areas}"))
        self.stdout.write(self.style.SUCCESS(f"✔ Total de subáreas: {total_subareas}"))
