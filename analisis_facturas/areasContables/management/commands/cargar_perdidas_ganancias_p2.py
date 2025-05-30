from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la segunda parte (áreas 12 a 17) de la Sección D: Cuenta de Pérdidas y Ganancias'

    def handle(self, *args, **options):
        seccion_d, _ = SeccionContable.objects.get_or_create(
            letra="D",
            defaults={"nombre": "CUENTA DE PÉRDIDAS Y GANANCIAS"}
        )

        estructura = [
            ("Ingresos financieros", "INGFIN", "12. Ingresos financieros", [
                ("a1) En empresas del grupo y asociadas", "7600,7601", ""),
                ("a2) En terceros", "7602,7603", ""),
                ("b1) De empresas del grupo y asociadas", "7610,7611,76200,76201,76210,76211", ""),
                ("b2) De terceros", "7612,7613,76202,76203,76212,76213,767,769", ""),
            ]),
            ("Gastos financieros", "GASF", "13. Gastos financieros", [
                ("a) Deudas con grupo y asociadas", "", "6610,6611,6615,6616,6620,6621,6640,6641,6650,6651,6654,6655"),
                ("b) Deudas con terceros", "", "6612,6613,6617,6618,6622,6623,6624,6642,6643,6652,6653,6656,6657,669"),
                ("c) Actualización de provisiones", "", "660"),
            ]),
            ("Variación valor razonable en instrumentos", "VARVAL", "14. Variación de valor razonable en instrumentos financieros", [
                ("a) Cambios en PyG", "7630,7631,7633", "6630,6631,6633"),
                ("b) Transferencias desde patrimonio neto", "7632", "6632"),
            ]),
            ("Diferencias de cambio", "CAMBIO", "15. Diferencias de cambio", [
                ("Diferencias de cambio", "768", "668"),
            ]),
            ("Deterioro y enajenación de instrumentos financieros", "ENAJFIN", "16. Deterioro y resultado por enajenaciones de instrumentos financieros", [
                ("a) Deterioros y pérdidas", "796,797,798,799", "696,697,698,699"),
                ("b) Enajenaciones y otras", "766,773,775", "666,667,673,675"),
            ]),
            ("Impuestos sobre beneficios", "IMP", "17. Impuestos sobre beneficios", [
                ("Impuestos sobre beneficios", "638", "6300,6301,633"),
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

        self.stdout.write(self.style.SUCCESS("✅ Carga de áreas 12–17 de la Sección D completada correctamente."))
