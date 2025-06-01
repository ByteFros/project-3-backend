from django.core.management.base import BaseCommand
from django.utils import timezone
from areasContables.models import SeccionContable, AreaContable, SubAreaContable, LineaFactura
from areasContables.utils.utils import buscar_subarea_por_cuenta
from decimal import Decimal
from collections import defaultdict


class Command(BaseCommand):
    help = 'Diagnostica la configuracion de areas contables y el problema con codigo 703'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detallado',
            action='store_true',
            help='Muestra informacion detallada adicional',
        )
        parser.add_argument(
            '--solo-703',
            action='store_true',
            help='Solo analiza el codigo 703',
        )

    def handle(self, *args, **options):
        self.detallado = options['detallado']
        self.solo_703 = options['solo_703']
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("DIAGNOSTICO DE AREAS CONTABLES"))
        self.stdout.write("=" * 70)
        
        if self.solo_703:
            self.analizar_codigo_703()
        else:
            self.diagnostico_completo()
        
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("DIAGNOSTICO COMPLETADO"))
        self.stdout.write("=" * 70)

    def diagnostico_completo(self):
        """Ejecuta el diagnostico completo"""
        
        # 1. Verificar secciones
        self.verificar_secciones()
        
        # 2. Verificar Seccion D
        seccion_d = self.verificar_seccion_d()
        
        # 3. Analizar codigo 703
        self.analizar_codigo_703()
        
        # 4. Probar funcion de busqueda
        self.probar_busqueda()
        
        # 5. Estadisticas generales
        self.estadisticas_generales()
        
        # 6. Simulacion Estado de Resultados
        if seccion_d:
            self.simular_estado_resultados(seccion_d)
        
        # 7. Diagnostico final
        self.diagnostico_final()

    def verificar_secciones(self):
        """Verifica las secciones configuradas"""
        self.stdout.write("\n1. SECCIONES CONFIGURADAS:")
        
        secciones = SeccionContable.objects.all()
        if secciones.exists():
            for seccion in secciones:
                self.stdout.write(f"   {seccion.letra} - {seccion.nombre}")
        else:
            self.stdout.write(self.style.ERROR("   No hay secciones configuradas"))
        
        return secciones

    def verificar_seccion_d(self):
        """Verifica la configuracion de la Seccion D"""
        self.stdout.write("\n2. SECCION D (Estado de Resultados):")
        
        seccion_d = SeccionContable.objects.filter(letra="D").first()
        
        if not seccion_d:
            self.stdout.write(self.style.ERROR("   ERROR: No existe Seccion D"))
            self.stdout.write("   SOLUCION: Crear seccion D para Estado de Resultados")
            return None
        
        self.stdout.write(self.style.SUCCESS(f"   OK: {seccion_d.nombre}"))
        
        # Verificar areas en Seccion D
        areas_d = AreaContable.objects.filter(seccion=seccion_d)
        if not areas_d.exists():
            self.stdout.write(self.style.ERROR("   ERROR: No hay areas en Seccion D"))
        else:
            self.stdout.write(f"   {areas_d.count()} areas configuradas:")
            
            total_lineas_seccion_d = 0
            for area in areas_d:
                subareas = SubAreaContable.objects.filter(area=area)
                self.stdout.write(f"\n     Area: {area.nombre}")
                
                if not subareas.exists():
                    self.stdout.write(self.style.WARNING("       Sin subareas configuradas"))
                else:
                    area_lineas = 0
                    for subarea in subareas:
                        lineas_count = LineaFactura.objects.filter(subarea=subarea).count()
                        area_lineas += lineas_count
                        
                        if self.detallado:
                            self.stdout.write(f"       - {subarea.nombre}")
                            self.stdout.write(f"         Codigos(+): {subarea.codigos_positivos}")
                            if subarea.codigos_negativos:
                                self.stdout.write(f"         Codigos(-): {subarea.codigos_negativos}")
                            self.stdout.write(f"         Lineas: {lineas_count}")
                    
                    total_lineas_seccion_d += area_lineas
                    self.stdout.write(f"     Total lineas en area: {area_lineas}")
            
            self.stdout.write(f"\n   TOTAL LINEAS EN SECCION D: {total_lineas_seccion_d}")
        
        return seccion_d

    def analizar_codigo_703(self):
        """Analiza especificamente el codigo 703"""
        self.stdout.write("\n3. ANALISIS CODIGO 703:")
        
        # Buscar lineas con codigo 703
        lineas_703 = LineaFactura.objects.filter(cuenta__startswith="703")
        total_703 = lineas_703.count()
        
        if total_703 == 0:
            self.stdout.write(self.style.ERROR("   ERROR: No se encontraron lineas con codigo 703"))
            self.stdout.write("   INFO: Verificar si los datos fueron importados correctamente")
            return
        
        self.stdout.write(self.style.SUCCESS(f"   OK: {total_703} lineas con codigo 703 encontradas"))
        
        # Verificar clasificacion
        clasificadas_703 = lineas_703.filter(subarea__isnull=False).count()
        no_clasificadas_703 = total_703 - clasificadas_703
        
        self.stdout.write(f"   Clasificadas: {clasificadas_703}")
        self.stdout.write(f"   No clasificadas: {no_clasificadas_703}")
        
        # Calcular totales monetarios
        total_debe_703 = sum(linea.debe or Decimal(0) for linea in lineas_703)
        total_haber_703 = sum(linea.haber or Decimal(0) for linea in lineas_703)
        
        self.stdout.write(f"\n   TOTALES MONETARIOS:")
        self.stdout.write(f"   Debe: {total_debe_703}")
        self.stdout.write(f"   Haber: {total_haber_703}")
        self.stdout.write(f"   Balance: {total_haber_703 - total_debe_703}")
        
        # Mostrar ejemplos
        self.stdout.write(f"\n   EJEMPLOS DE LINEAS 703:")
        for i, linea in enumerate(lineas_703[:5]):
            estado = self.style.SUCCESS("CLASIFICADA") if linea.subarea else self.style.ERROR("NO CLASIFICADA")
            self.stdout.write(f"      {i+1}. {linea.cuenta}: Debe={linea.debe}, Haber={linea.haber}")
            self.stdout.write(f"         Estado: {estado}")
            
            if linea.subarea:
                self.stdout.write(f"         Subarea: {linea.subarea.nombre}")
                self.stdout.write(f"         Area: {linea.subarea.area.nombre}")
                self.stdout.write(f"         Seccion: {linea.subarea.area.seccion.letra}")
            
            if linea.nombre and self.detallado:
                self.stdout.write(f"         Nombre: {linea.nombre}")
        
        # Analizar donde estan clasificadas las lineas 703
        if clasificadas_703 > 0:
            self.stdout.write(f"\n   DISTRIBUCION POR SECCION:")
            secciones_703 = defaultdict(int)
            
            for linea in lineas_703.filter(subarea__isnull=False):
                seccion = linea.subarea.area.seccion.letra
                secciones_703[seccion] += 1
            
            for seccion, count in secciones_703.items():
                self.stdout.write(f"   Seccion {seccion}: {count} lineas")

    def probar_busqueda(self):
        """Prueba la funcion de busqueda de subareas"""
        self.stdout.write("\n4. PRUEBA FUNCION buscar_subarea_por_cuenta:")
        
        codigos_prueba = ["703", "703.0001", "700", "701", "702", "704", "705"]
        
        for codigo in codigos_prueba:
            try:
                subarea = buscar_subarea_por_cuenta(codigo)
                if subarea:
                    self.stdout.write(self.style.SUCCESS(f"   OK: {codigo} -> {subarea.nombre}"))
                    if self.detallado:
                        self.stdout.write(f"      Area: {subarea.area.nombre}")
                        self.stdout.write(f"      Seccion: {subarea.area.seccion.letra}")
                else:
                    self.stdout.write(self.style.ERROR(f"   ERROR: {codigo} -> No encontrado"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   FALLA: {codigo} -> Error: {e}"))

    def estadisticas_generales(self):
        """Muestra estadisticas generales de clasificacion"""
        self.stdout.write("\n5. ESTADISTICAS GENERALES:")
        
        total_lineas = LineaFactura.objects.count()
        lineas_clasificadas = LineaFactura.objects.filter(subarea__isnull=False).count()
        lineas_no_clasificadas = total_lineas - lineas_clasificadas
        
        porcentaje_clasificado = (lineas_clasificadas / total_lineas * 100) if total_lineas > 0 else 0
        
        self.stdout.write(f"   Total lineas en BD: {total_lineas}")
        self.stdout.write(f"   Lineas clasificadas: {lineas_clasificadas} ({porcentaje_clasificado:.1f}%)")
        self.stdout.write(f"   Lineas no clasificadas: {lineas_no_clasificadas}")
        
        if lineas_no_clasificadas > 0 and self.detallado:
            # Mostrar ejemplos de cuentas no clasificadas
            cuentas_no_clasificadas = set()
            for linea in LineaFactura.objects.filter(subarea__isnull=True)[:50]:
                cuenta_base = linea.cuenta.split('.')[0] if '.' in linea.cuenta else linea.cuenta
                cuentas_no_clasificadas.add(cuenta_base)
            
            self.stdout.write(f"\n   EJEMPLOS DE CUENTAS NO CLASIFICADAS:")
            for cuenta in sorted(list(cuentas_no_clasificadas)[:10]):
                count = LineaFactura.objects.filter(cuenta__startswith=cuenta, subarea__isnull=True).count()
                self.stdout.write(f"      {cuenta}*: {count} lineas")

    def simular_estado_resultados(self, seccion_d):
        """Simula el Estado de Resultados actual"""
        self.stdout.write("\n6. SIMULACION ESTADO DE RESULTADOS:")
        
        areas_d = AreaContable.objects.filter(seccion=seccion_d)
        
        if not areas_d.exists():
            self.stdout.write(self.style.ERROR("   ERROR: No hay areas en Seccion D"))
            return
        
        total_debe_er = Decimal(0)
        total_haber_er = Decimal(0)
        areas_con_datos = 0
        lineas_703_incluidas = 0
        
        for area in areas_d:
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            area_tiene_703 = False
            
            for subarea in area.subareas.all():
                lineas = LineaFactura.objects.filter(subarea=subarea)
                debe = sum(linea.debe or Decimal(0) for linea in lineas)
                haber = sum(linea.haber or Decimal(0) for linea in lineas)
                
                # Contar lineas 703
                lineas_703_en_subarea = lineas.filter(cuenta__startswith="703").count()
                if lineas_703_en_subarea > 0:
                    lineas_703_incluidas += lineas_703_en_subarea
                    area_tiene_703 = True
                    if self.detallado:
                        self.stdout.write(f"   {subarea.nombre}: {lineas_703_en_subarea} lineas 703")
                
                area_debe += debe
                area_haber += haber
            
            if area_debe > 0 or area_haber > 0:
                areas_con_datos += 1
                estado_703 = self.style.SUCCESS("(incluye 703)") if area_tiene_703 else ""
                self.stdout.write(f"   {area.nombre}: Debe={area_debe}, Haber={area_haber} {estado_703}")
            
            total_debe_er += area_debe
            total_haber_er += area_haber
        
        self.stdout.write(f"\n   TOTALES ESTADO DE RESULTADOS:")
        self.stdout.write(f"   Debe: {total_debe_er}")
        self.stdout.write(f"   Haber: {total_haber_er}")
        self.stdout.write(f"   Balance: {total_haber_er - total_debe_er}")
        self.stdout.write(f"   Areas con datos: {areas_con_datos}")
        
        if lineas_703_incluidas > 0:
            self.stdout.write(self.style.SUCCESS(f"   Lineas 703 incluidas: {lineas_703_incluidas}"))
        else:
            self.stdout.write(self.style.ERROR(f"   Lineas 703 incluidas: 0"))
        
        # Verificar si hay problema
        lineas_703_total = LineaFactura.objects.filter(cuenta__startswith="703").count()
        if lineas_703_incluidas == 0 and lineas_703_total > 0:
            self.stdout.write(self.style.ERROR("   PROBLEMA: Hay lineas 703 pero no aparecen en Estado de Resultados"))

    def diagnostico_final(self):
        """Genera el diagnostico final con recomendaciones"""
        self.stdout.write("\n7. DIAGNOSTICO FINAL:")
        
        # Verificar problemas
        problemas = []
        
        seccion_d = SeccionContable.objects.filter(letra="D").first()
        if not seccion_d:
            problemas.append("No existe Seccion D")
        else:
            areas_d = AreaContable.objects.filter(seccion=seccion_d)
            if not areas_d.exists():
                problemas.append("Seccion D sin areas")
        
        lineas_703 = LineaFactura.objects.filter(cuenta__startswith="703")
        total_703 = lineas_703.count()
        clasificadas_703 = lineas_703.filter(subarea__isnull=False).count()
        
        if total_703 > 0 and clasificadas_703 == 0:
            problemas.append("Lineas 703 existen pero no estan clasificadas")
        
        # Verificar si estan en Estado de Resultados
        if seccion_d and areas_d.exists():
            lineas_703_en_er = 0
            for area in areas_d:
                for subarea in area.subareas.all():
                    lineas_703_en_er += LineaFactura.objects.filter(
                        subarea=subarea, cuenta__startswith="703"
                    ).count()
            
            if total_703 > 0 and clasificadas_703 > 0 and lineas_703_en_er == 0:
                problemas.append("Lineas 703 clasificadas pero no en Seccion D")
        
        # Verificar porcentaje general
        total_lineas = LineaFactura.objects.count()
        lineas_clasificadas = LineaFactura.objects.filter(subarea__isnull=False).count()
        porcentaje = (lineas_clasificadas / total_lineas * 100) if total_lineas > 0 else 0
        
        if porcentaje < 50:
            problemas.append(f"Bajo porcentaje de clasificacion ({porcentaje:.1f}%)")
        
        # Mostrar resultados
        if problemas:
            self.stdout.write(self.style.ERROR("   PROBLEMAS IDENTIFICADOS:"))
            for i, problema in enumerate(problemas, 1):
                self.stdout.write(f"   {i}. {problema}")
            
            self.stdout.write(self.style.WARNING("\n   RECOMENDACIONES:"))
            
            if "No existe Seccion D" in problemas:
                self.stdout.write("   1. Ejecutar: python manage.py configurar_areas")
            
            if "Seccion D sin areas" in problemas:
                self.stdout.write("   2. Crear areas en Seccion D para ingresos/gastos")
            
            if any("703" in p for p in problemas):
                self.stdout.write("   3. Configurar subarea para codigo 703 en Seccion D")
                self.stdout.write("      - Area: 'Importe neto de la cifra de negocios'")
                self.stdout.write("      - Subarea: 'b) Prestaciones de servicios'")
                self.stdout.write("      - Codigos: '703,704,705'")
            
            self.stdout.write(self.style.SUCCESS("\n   SIGUIENTE PASO:"))
            self.stdout.write("   python manage.py configurar_areas --auto")
            
        else:
            self.stdout.write(self.style.SUCCESS("   CONFIGURACION CORRECTA!"))
            self.stdout.write("   No se encontraron problemas graves.")
            
            if total_703 > 0:
                lineas_703_en_er = 0
                if seccion_d:
                    areas_d = AreaContable.objects.filter(seccion=seccion_d)
                    for area in areas_d:
                        for subarea in area.subareas.all():
                            lineas_703_en_er += LineaFactura.objects.filter(
                                subarea=subarea, cuenta__startswith="703"
                            ).count()
                
                if lineas_703_en_er > 0:
                    self.stdout.write(f"   Las {lineas_703_en_er} lineas 703 SI estan en Estado de Resultados")
                else:
                    self.stdout.write("   Las lineas 703 no estan en Estado de Resultados")
                    self.stdout.write("   (Esto podria ser correcto segun tu plan contable)")
