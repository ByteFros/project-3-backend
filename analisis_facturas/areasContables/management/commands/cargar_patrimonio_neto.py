from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la parte de Patrimonio Neto dentro de la Sección C: Patrimonio Neto y Pasivo'

    def handle(self, *args, **options):
        # Crear sección C si no existe
        seccion_c, _ = SeccionContable.objects.get_or_create(
            letra="C",
            defaults={"nombre": "PATRIMONIO NETO Y PASIVO"}
        )

        estructura = [
            ("Capital", "CAP", "Capital social y no exigido", [
                ("Capital escriturado", "100,101,102", ""),
                ("Capital no exigido", "", "1030,1040"),
            ]),
            ("Prima de emisión", "PE", "Aportaciones adicionales al capital", [
                ("Prima de emisión", "110", ""),
            ]),
            ("Reservas", "RES", "Reservas acumuladas", [
                ("Legal y estatutarias", "112,1141", ""),
                ("Otras reservas", "113,1140,1142,1143,1144,115,119", ""),
            ]),
            ("Acciones y participaciones propias", "ACC", "Participaciones propias en el patrimonio", [
                ("Acciones y participaciones propias", "", "108,109"),
            ]),
            ("Resultados de ejercicios anteriores", "RESEJ", "Resultados acumulados de ejercicios previos", [
                ("Remanente", "120", ""),
                ("Resultados negativos", "", "121"),
            ]),
            ("Otras aportaciones de socios", "OAS", "Aportaciones no reflejadas como capital", [
                ("Otras aportaciones de socios", "118", ""),
            ]),
            ("Resultado del ejercicio", "REJ", "Beneficio o pérdida del periodo actual", [
                ("Resultado del ejercicio", "129", ""),
            ]),
            ("Dividendo a cuenta", "DIV", "Dividendo anticipado a socios", [
                ("Dividendo a cuenta", "", "557"),
            ]),
            ("Otros instrumentos de patrimonio", "INST", "Otros instrumentos representativos del patrimonio neto", [
                ("Otros instrumentos de patrimonio", "111", ""),
            ]),
            ("Activos financieros a valor razonable", "AFVR", "Ajustes por activos financieros", [
                ("Activos financieros a valor razonable", "133", ""),
            ]),
            ("Operaciones de cobertura", "COVER", "Coberturas de flujos de efectivo", [
                ("Operaciones de cobertura", "1340", ""),
            ]),
            ("Otros ajustes de valor", "AJVAL", "Otros ajustes contables al valor del patrimonio", [
                ("Otros ajustes de valor", "137", ""),
            ]),
            ("Subvenciones y donaciones recibidas", "SUBV", "Subvenciones, donaciones y legados no reintegrables", [
                ("Subvenciones y donaciones", "130,131,132", ""),
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa del Patrimonio Neto realizada correctamente."))
