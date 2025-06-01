from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga áreas 1-11 de Pérdidas y Ganancias con numeración exacta BOE para cálculo RESULTADO DE EXPLOTACIÓN'

    def handle(self, *args, **options):
        seccion_d, _ = SeccionContable.objects.get_or_create(
            letra="D",
            defaults={"nombre": "D) CUENTA DE PÉRDIDAS Y GANANCIAS"}
        )

        estructura = [
            ("1. Importe neto de la cifra de negocios", "VENTAS", "1. Importe neto de la cifra de negocios", [
                ("a) Ventas", "700,701,702,703,704", "706,708,709"),
                ("b) Prestaciones de servicios", "705", ""),
            ]),
            ("2. Variación de existencias de productos terminados y en curso de fabricación", "VARIEX", "2. Variación de existencias de productos terminados y en curso de fabricación", [
                ("Variación de existencias de productos terminados y en curso de fabricación", "71,7930", "6930"),
            ]),
            ("3. Trabajos realizados por la empresa para su activo", "TRABACT", "3. Trabajos realizados por la empresa para su activo", [
                ("Trabajos realizados por la empresa para su activo", "73", ""),
            ]),
            ("4. Aprovisionamientos", "APROV", "4. Aprovisionamientos", [
                ("a) Consumo de mercaderías", "6060,6080,6090,610", "600"),
                ("b) Consumo de materias primas y otras materias consumibles", "6061,6062,6081,6082,6091,6092,611,612", "601,602"),
                ("c) Trabajos realizados por otras empresas", "", "607"),
                ("d) Deterioro de mercaderías, materias primas y otros aprovisionamientos", "7931,7932,7933", "6931,6932,6933"),
            ]),
            ("5. Otros ingresos de explotación", "INGEXP", "5. Otros ingresos de explotación", [
                ("a) Ingresos accesorios y otros de gestión corriente", "75", ""),
                ("b) Subvenciones de explotación incorporadas al resultado del ejercicio", "740,747", ""),
            ]),
            ("6. Gastos de personal", "GPER", "6. Gastos de personal", [
                ("a) Sueldos, salarios y asimilados", "", "640,641,6450"),
                ("b) Cargas sociales", "", "642,643,649"),
                ("c) Provisiones", "7950,7957", "644,6457"),
            ]),
            ("7. Otros gastos de explotación", "GEXP", "7. Otros gastos de explotación", [
                ("a) Servicios exteriores", "", "62"),
                ("b) Tributos", "636,639", "631,634"),
                ("c) Pérdidas, deterioro y variación de provisiones por operaciones comerciales", "794,7954", "650,694,695"),
                ("d) Otros gastos de gestión corriente", "", "651,659"),
            ]),
            ("8. Amortización del inmovilizado", "AMORT", "8. Amortización del inmovilizado", [
                ("Amortización del inmovilizado", "", "68"),
            ]),
            ("9. Imputación de subvenciones de inmovilizado no financiero y otras", "SUBVIM", "9. Imputación de subvenciones de inmovilizado no financiero y otras", [
                ("Imputación de subvenciones de inmovilizado no financiero y otras", "746", ""),
            ]),
            ("10. Excesos de provisiones", "EXCESP", "10. Excesos de provisiones", [
                ("Excesos de provisiones", "7951,7952,7955,7956", ""),
            ]),
            ("11. Deterioro y resultado por enajenaciones del inmovilizado", "ENAJINMO", "11. Deterioro y resultado por enajenaciones del inmovilizado", [
                ("a) Deterioros y pérdidas", "790,791,792", "690,691,692"),
                ("b) Resultados por enajenaciones y otras", "770,771,772", "670,671,672"),
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

        self.stdout.write(self.style.SUCCESS("✅ Carga de áreas 1–11 (RESULTADO DE EXPLOTACIÓN) completada correctamente."))
