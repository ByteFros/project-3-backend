from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la SECCIÓN B: Activo Corriente con áreas y subáreas contables según BOE'

    def handle(self, *args, **options):
        # Crear sección B
        seccion_b, _ = SeccionContable.objects.get_or_create(
            letra="B",
            defaults={"nombre": "ACTIVO CORRIENTE"}
        )

        estructura = [
            ("Activos no corrientes mantenidos para la venta", "ANCMV", "Activos que se espera vender a corto plazo", [
                ("Activos mantenidos para la venta", "580,581,582,583,584", "599"),
            ]),

            ("Existencias", "EXIS", "Inventario de productos y materiales", [
                ("Comerciales", "30", "390"),
                ("Materias primas y otros aprovisionamientos", "31,32", "391,392"),
                ("Productos en curso", "33,34", "393,394"),
                ("Productos terminados", "35", "395"),
                ("Subproductos, residuos y materiales recuperados", "36", "396"),
                ("Anticipos a proveedores", "407", ""),
            ]),

            ("Deudores comerciales y otras cuentas a cobrar", "DEUD", "Clientes, impuestos a cobrar, personal", [
                ("Clientes por ventas y servicios", "430,431,432,435,436", "437,490,4935"),
                ("Clientes empresas del grupo", "433,434", "4933,4934"),
                ("Deudores varios", "44", ""),
                ("Personal", "460,544", ""),
                ("Impuesto corriente", "4709", ""),
                ("Otros créditos con Administraciones Públicas", "4700,4708,471,472", ""),
                ("Accionistas por desembolsos exigidos", "5580", ""),
            ]),

            ("Inversiones en empresas del grupo y asociadas (CP)", "INVGRUCP", "Inversiones temporales en empresas del grupo", [
                ("Instrumentos de patrimonio", "5303,5304", "5393,5394,593"),
                ("Créditos a empresas", "5323,5324,5343,5344", "5953,5954"),
                ("Valores representativos de deuda", "5313,5314,5333,5334", "5943,5944"),
                ("Derivados", "", ""),
                ("Otros activos financieros", "5353,5354,5523,5524", ""),
            ]),

            ("Inversiones financieras a corto plazo", "INVFINCP", "Activos financieros a corto plazo con terceros", [
                ("Instrumentos de patrimonio", "5305,540", "5395,549"),
                ("Créditos a empresas", "5325,5345,542,543,547", "5955,598"),
                ("Valores representativos de deuda", "5315,5335,541,546", "5945,597"),
                ("Derivados", "5590,5593", ""),
                ("Otros activos financieros", "5355,545,548,551,5525,565,566", ""),
            ]),

            ("Periodificaciones a corto plazo", "PERCP", "Gastos e ingresos temporales a corto plazo", [
                ("Periodificaciones a corto plazo", "480,567", ""),
            ]),

            ("Efectivo y otros activos líquidos equivalentes", "TES", "Caja y bancos", [
                ("Tesorería", "570,571,572,573,574,575", ""),
                ("Otros activos líquidos equivalentes", "576", ""),
            ]),
        ]

        for nombre, abrev, descripcion, subareas in estructura:
            area, created = AreaContable.objects.get_or_create(
                nombre=nombre,
                seccion=seccion_b,
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa de la Sección B finalizada correctamente."))
