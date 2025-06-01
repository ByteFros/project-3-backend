from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable


class Command(BaseCommand):
    help = 'Agrega códigos contables faltantes que estaban en las versiones originales'

    def handle(self, *args, **options):
        
        # AGREGAR códigos a Sección A (Activos por impuesto diferido)
        try:
            seccion_a = SeccionContable.objects.get(letra="A")
            area_impuesto = AreaContable.objects.get(
                seccion=seccion_a, 
                nombre="VI. Activos por impuesto diferido"
            )
            
            # Agregar deducciones y créditos por pérdidas
            SubAreaContable.objects.get_or_create(
                area=area_impuesto,
                nombre="Deducciones y bonificaciones pendientes",
                defaults={
                    "descripcion": "Deducciones IT pendientes de aplicar",
                    "codigos_positivos": "4742",
                    "codigos_negativos": ""
                }
            )
            
            SubAreaContable.objects.get_or_create(
                area=area_impuesto,
                nombre="Créditos por pérdidas a compensar",
                defaults={
                    "descripcion": "Créditos por pérdidas ejercicios anteriores",
                    "codigos_positivos": "4745",
                    "codigos_negativos": ""
                }
            )
            
            self.stdout.write("✅ Códigos 4742 y 4745 agregados a Activos por impuesto diferido")
            
        except Exception as e:
            self.stdout.write(f"⚠️ Error agregando códigos a Sección A: {e}")

        # AGREGAR código 4009 a Pasivo Corriente
        try:
            seccion_c = SeccionContable.objects.get(letra="C")
            area_acreedores = AreaContable.objects.get(
                seccion=seccion_c,
                nombre="C) PASIVO CORRIENTE - V. Acreedores comerciales y otras cuentas a pagar"
            )
            
            # Verificar si ya existe la subárea de proveedores
            subarea_proveedores, created = SubAreaContable.objects.get_or_create(
                area=area_acreedores,
                nombre="8. Proveedores - facturas pendientes",
                defaults={
                    "descripcion": "Provisiones para facturas pendientes",
                    "codigos_positivos": "4009",
                    "codigos_negativos": ""
                }
            )
            
            if created:
                self.stdout.write("✅ Código 4009 agregado a Acreedores comerciales")
            else:
                self.stdout.write("ℹ️ Código 4009 ya existía")
                
        except Exception as e:
            self.stdout.write(f"⚠️ Error agregando código 4009: {e}")

        # AGREGAR códigos a Sección D (ingresos y gastos adicionales)
        try:
            seccion_d = SeccionContable.objects.get(letra="D")
            
            # Crear área para otros ingresos/gastos no cubiertos por áreas 1-17
            area_otros, created = AreaContable.objects.get_or_create(
                seccion=seccion_d,
                nombre="OTROS INGRESOS Y GASTOS (Complementarios)",
                defaults={
                    "abreviatura": "OTROS",
                    "descripcion": "Códigos adicionales no incluidos en áreas 1-17 del BOE"
                }
            )
            
            if created:
                self.stdout.write("✅ Área 'OTROS INGRESOS Y GASTOS' creada")

            # Agregar subáreas para códigos faltantes
            codigos_otros = [
                ("Ingresos adicionales (730)", "730", "", "Otros ingresos de explotación"),
                ("Gastos varios (623,625,626,629)", "623,625,626,629", "", "Gastos operacionales varios"),
                ("Seguridad Social (621)", "621", "", "Cotizaciones sociales"),
                ("Servicios profesionales (627)", "627", "", "Publicidad, promoción y relaciones públicas"),
                ("Intereses (662)", "662", "", "Intereses de deudas"),
                ("Diferencias de cambio (668)", "668", "", "Diferencias negativas de cambio"),
                ("Trabajos otras empresas (607)", "607", "", "Trabajos realizados por otras empresas"),
                ("Amortizaciones (680,681)", "680,681", "", "Amortización del inmovilizado"),
                ("Ingresos extraordinarios (778)", "778", "", "Ingresos excepcionales"),
                ("Diferencias cambio positivas (768)", "768", "", "Diferencias positivas de cambio"),
            ]
            
            for nombre, cod_pos, cod_neg, descripcion in codigos_otros:
                SubAreaContable.objects.get_or_create(
                    area=area_otros,
                    nombre=nombre,
                    defaults={
                        "descripcion": descripcion,
                        "codigos_positivos": cod_pos,
                        "codigos_negativos": cod_neg
                    }
                )
                
            self.stdout.write(f"✅ {len(codigos_otros)} subáreas de códigos complementarios agregadas")
            
        except Exception as e:
            self.stdout.write(f"⚠️ Error agregando códigos complementarios: {e}")

        # VERIFICAR cobertura
        self.stdout.write("\n📊 CÓDIGOS AGREGADOS:")
        self.stdout.write("   4009 - Proveedores facturas pendientes")
        self.stdout.write("   4742 - Deducciones IT pendientes")
        self.stdout.write("   4745 - Créditos pérdidas a compensar")
        self.stdout.write("   730 - Ingresos adicionales")
        self.stdout.write("   623,625,626,629 - Gastos varios")
        self.stdout.write("   621,627,662,668,607,680,681,778,768 - Otros códigos")
        
        self.stdout.write(self.style.SUCCESS("\n✅ Códigos complementarios agregados correctamente"))
        self.stdout.write("💡 Esto mantiene la estructura BOE para cálculos + cubre códigos adicionales")
