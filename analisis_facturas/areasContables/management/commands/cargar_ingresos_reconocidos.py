
from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la Sección G: Ingresos y Gastos Reconocidos con estructura oficial del BOE'

    def handle(self, *args, **options):
        seccion_g, _ = SeccionContable.objects.get_or_create(
            letra="G",
            defaults={"nombre": "G) INGRESOS Y GASTOS RECONOCIDOS"}
        )

        estructura = [
            # A) INGRESOS Y GASTOS IMPUTADOS DIRECTAMENTE AL PATRIMONIO NETO
            ("I. Valoración instrumentos financieros", "VFIN", "Activos financieros a valor razonable con cambios en PN", [
                ("1. Activos financieros a valor razonable", "800,900,991", ""),
                ("2. Otros ingresos/gastos", "89", "")
            ]),
            ("II. Coberturas de flujos de efectivo", "COBERT", "Coberturas reconocidas en patrimonio", [
                ("Coberturas de flujos de efectivo", "810,910", "")
            ]),
            ("III. Subvenciones, donaciones y legados recibidos", "SUBVEN", "Ingresos reconocidos directamente", [
                ("Subvenciones y legados", "94", "")
            ]),
            ("IV. Ganancias y pérdidas actuariales y ajustes", "AJUSTES", "Otros ajustes patrimoniales", [
                ("Ajustes actuariales y otros", "95", "")
            ]),
            ("V. Efecto impositivo", "IMPON", "Efectos fiscales por ingresos/gastos en patrimonio", [
                ("Efecto impositivo", "8300,8301,833,834,835,838", "")
            ]),

            # B) TRANSFERENCIAS A PÉRDIDAS Y GANANCIAS
            ("VI. Transferencias de instrumentos financieros", "TRANSVFIN", "Traslado de valoración al resultado", [
                ("Transferencias por instrumentos financieros", "802,902,993,994", "")
            ]),
            ("VII. Transferencias de coberturas", "TRANSCOB", "Coberturas trasladadas al resultado", [
                ("Transferencias por coberturas", "812,912", "")
            ]),
            ("VIII. Transferencias de subvenciones y legados", "TRANSSUB", "Subvenciones transferidas al resultado", [
                ("Transferencias por subvenciones y legados", "84", "")
            ]),
            ("IX. Efecto impositivo de transferencias", "TRANIMP", "Impacto fiscal de transferencias", [
                ("Efecto impositivo de transferencias", "8301,836,837", "")
            ]),
        ]

        for nombre, abrev, descripcion, subareas in estructura:
            area, created = AreaContable.objects.get_or_create(
                nombre=nombre,
                seccion=seccion_g,
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

        self.stdout.write(self.style.SUCCESS("✅ Sección G cargada correctamente con estructura BOE."))
