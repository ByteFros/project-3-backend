from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Carga la SECCIÓN B: Activo Corriente con nomenclatura exacta del BOE'

    def handle(self, *args, **options):
        # Crear sección B con nomenclatura BOE
        seccion_b, _ = SeccionContable.objects.get_or_create(
            letra="B",
            defaults={"nombre": "B) ACTIVO CORRIENTE"}
        )

        estructura = [
            ("I. Activos no corrientes mantenidos para la venta", "ANCMV", "Activos que se espera vender a corto plazo", [
                ("Activos no corrientes mantenidos para la venta", "580,581,582,583,584", "599"),
            ]),

            ("II. Existencias", "EXIS", "Inventario de productos y materiales", [
                ("1. Comerciales", "30", "390"),
                ("2. Materias primas y otros aprovisionamientos", "31,32", "391,392"),
                ("3. Productos en curso", "33,34", "393,394"),
                ("4. Productos terminados", "35", "395"),
                ("5. Subproductos, residuos y materiales recuperados", "36", "396"),
                ("6. Anticipos a proveedores", "407", ""),
            ]),

            ("III. Deudores comerciales y otras cuentas a cobrar", "DEUD", "Clientes, impuestos a cobrar, personal", [
                ("1. Clientes por ventas y prestaciones de servicios", "430,431,432,435,436", "437,490,4935"),
                ("2. Clientes, empresas del grupo y asociadas", "433,434", "4933,4934"),
                ("3. Deudores varios", "44", ""),
                ("4. Personal", "460,544", ""),
                ("5. Activos por impuesto corriente", "4709", ""),
                ("6. Otros créditos con las Administraciones Públicas", "4700,4708,471,472", ""),
                ("7. Accionistas (socios) por desembolsos exigidos", "5580", ""),
            ]),

            ("IV. Inversiones en empresas del grupo y asociadas a corto plazo", "INVGRUCP", "Inversiones temporales en empresas del grupo", [
                ("1. Instrumentos de patrimonio", "5303,5304", "5393,5394,593"),
                ("2. Créditos a empresas", "5323,5324,5343,5344", "5953,5954"),
                ("3. Valores representativos de deuda", "5313,5314,5333,5334", "5943,5944"),
                ("4. Derivados", "", ""),
                ("5. Otros activos financieros", "5353,5354,5523,5524", ""),
            ]),

            ("V. Inversiones financieras a corto plazo", "INVFINCP", "Activos financieros a corto plazo con terceros", [
                ("1. Instrumentos de patrimonio", "5305,540", "5395,549"),
                ("2. Créditos a empresas", "5325,5345,542,543,547", "5955,598"),
                ("3. Valores representativos de deuda", "5315,5335,541,546", "5945,597"),
                ("4. Derivados", "5590,5593", ""),
                ("5. Otros activos financieros", "5355,545,548,551,5525,565,566", ""),
            ]),

            ("VI. Periodificaciones a corto plazo", "PERCP", "Gastos e ingresos temporales a corto plazo", [
                ("Periodificaciones a corto plazo", "480,567", ""),
            ]),

            ("VII. Efectivo y otros activos líquidos equivalentes", "TES", "Caja y bancos", [
                ("1. Tesorería", "570,571,572,573,574,575", ""),
                ("2. Otros activos líquidos equivalentes", "576", ""),
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

        self.stdout.write(self.style.SUCCESS("✅ Carga completa de la Sección B (nomenclatura BOE) finalizada correctamente."))
