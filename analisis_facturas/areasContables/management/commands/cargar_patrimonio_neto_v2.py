from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga Patrimonio Neto con estructura exacta del BOE para cálculos correctos'

    def handle(self, *args, **options):
        # Crear sección C con nomenclatura BOE
        seccion_c, _ = SeccionContable.objects.get_or_create(
            letra="C",
            defaults={"nombre": "C) PATRIMONIO NETO"}
        )

        estructura = [
            # A) PATRIMONIO NETO - A-1) Fondos propios
            ("A) PATRIMONIO NETO - A-1) Fondos propios - I. Capital", "CAP", "Capital social y no exigido", [
                ("1. Capital escriturado", "100,101,102", ""),
                ("2. (Capital no exigido)", "", "1030,1040"),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - II. Prima de emisión", "PE", "Aportaciones adicionales al capital", [
                ("Prima de emisión", "110", ""),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - III. Reservas", "RES", "Reservas acumuladas", [
                ("1. Legal y estatutarias", "112,1141", ""),
                ("2. Otras reservas", "113,1140,1142,1143,1144,115,119", ""),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - IV. (Acciones y participaciones en patrimonio propias)", "ACC", "Participaciones propias en el patrimonio", [
                ("(Acciones y participaciones en patrimonio propias)", "", "108,109"),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - V. Resultados de ejercicios anteriores", "RESEJ", "Resultados acumulados de ejercicios previos", [
                ("1. Remanente", "120", ""),
                ("2. (Resultados negativos de ejercicios anteriores)", "", "121"),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - VI. Otras aportaciones de socios", "OAS", "Aportaciones no reflejadas como capital", [
                ("Otras aportaciones de socios", "118", ""),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - VII. Resultado del ejercicio", "REJ", "Beneficio o pérdida del periodo actual", [
                ("Resultado del ejercicio", "129", ""),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - VIII. (Dividendo a cuenta)", "DIV", "Dividendo anticipado a socios", [
                ("(Dividendo a cuenta)", "", "557"),
            ]),
            ("A) PATRIMONIO NETO - A-1) Fondos propios - IX. Otros instrumentos de patrimonio neto", "INST", "Otros instrumentos representativos del patrimonio neto", [
                ("Otros instrumentos de patrimonio neto", "111", ""),
            ]),
            
            # A) PATRIMONIO NETO - A-2) Ajustes por cambios de valor
            ("A) PATRIMONIO NETO - A-2) Ajustes por cambios de valor - I. Activos financieros", "AFVR", "Ajustes por activos financieros", [
                ("Activos financieros a valor razonable con cambios en el patrimonio neto", "133", ""),
            ]),
            ("A) PATRIMONIO NETO - A-2) Ajustes por cambios de valor - II. Operaciones de cobertura", "COVER", "Coberturas de flujos de efectivo", [
                ("Operaciones de cobertura", "1340", ""),
            ]),
            ("A) PATRIMONIO NETO - A-2) Ajustes por cambios de valor - III. Otros", "AJVAL", "Otros ajustes contables al valor del patrimonio", [
                ("Otros", "137", ""),
            ]),
            
            # A) PATRIMONIO NETO - A-3) Subvenciones, donaciones y legados recibidos
            ("A) PATRIMONIO NETO - A-3) Subvenciones, donaciones y legados recibidos", "SUBV", "Subvenciones, donaciones y legados no reintegrables", [
                ("Subvenciones, donaciones y legados recibidos", "130,131,132", ""),
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa del PATRIMONIO NETO (estructura BOE exacta) realizada correctamente."))
