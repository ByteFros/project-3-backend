from django.core.management.base import BaseCommand
from areasContables.models import SeccionContable, AreaContable, SubAreaContable, LineaFactura

class Command(BaseCommand):
    help = 'Reclasifica las cuentas 703 a la subarea correcta'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("RECLASIFICANDO CUENTAS 703"))
        self.stdout.write("=" * 60)
        
        # 1. Encontrar la subárea correcta
        try:
            subarea_correcta = SubAreaContable.objects.get(
                nombre="b) Prestaciones de servicios",
                area__nombre="Importe neto de la cifra de negocios"
            )
            self.stdout.write(f"✅ Subárea destino encontrada: {subarea_correcta.nombre}")
            self.stdout.write(f"   Área: {subarea_correcta.area.nombre}")
        except SubAreaContable.DoesNotExist:
            self.stdout.write(self.style.ERROR("❌ No se encontró la subárea 'b) Prestaciones de servicios'"))
            return
        
        # 2. Encontrar líneas con código 703
        lineas_703 = LineaFactura.objects.filter(cuenta__startswith="703")
        total_lineas = lineas_703.count()
        
        if total_lineas == 0:
            self.stdout.write(self.style.WARNING("⚠️ No se encontraron líneas con código 703"))
            return
        
        self.stdout.write(f"📊 Encontradas {total_lineas} líneas con código 703")
        
        # 3. Mostrar estado actual
        subarea_actual = lineas_703.first().subarea if lineas_703.exists() else None
        if subarea_actual:
            self.stdout.write(f"📍 Actualmente asignadas a: {subarea_actual.nombre}")
            self.stdout.write(f"   Área actual: {subarea_actual.area.nombre}")
        
        # 4. Actualizar códigos en la subárea destino
        codigos_actuales = subarea_correcta.codigos_positivos.split(',') if subarea_correcta.codigos_positivos else []
        codigos_actuales = [c.strip() for c in codigos_actuales if c.strip()]
        
        if '703' not in codigos_actuales:
            codigos_actuales.append('703')
            subarea_correcta.codigos_positivos = ','.join(codigos_actuales)
            subarea_correcta.save()
            self.stdout.write("✅ Código 703 añadido a 'b) Prestaciones de servicios'")
        
        # 5. Reclasificar todas las líneas
        lineas_actualizadas = 0
        for linea in lineas_703:
            linea.subarea = subarea_correcta
            linea.save()
            lineas_actualizadas += 1
        
        self.stdout.write(f"✅ {lineas_actualizadas} líneas reclasificadas exitosamente")
        
        # 6. Limpiar código 703 de la subárea anterior si es necesario
        if subarea_actual and subarea_actual != subarea_correcta:
            codigos_anteriores = subarea_actual.codigos_positivos.split(',') if subarea_actual.codigos_positivos else []
            codigos_anteriores = [c.strip() for c in codigos_anteriores if c.strip() and c.strip() != '703']
            subarea_actual.codigos_positivos = ','.join(codigos_anteriores)
            subarea_actual.save()
            self.stdout.write(f"🧹 Código 703 eliminado de '{subarea_actual.nombre}'")
        
        # 7. Verificar resultado
        from decimal import Decimal
        total_debe = sum(linea.debe or Decimal(0) for linea in lineas_703)
        total_haber = sum(linea.haber or Decimal(0) for linea in lineas_703)
        
        self.stdout.write("\n📊 RESULTADO:")
        self.stdout.write(f"   Líneas reclasificadas: {lineas_actualizadas}")
        self.stdout.write(f"   Total Debe: {total_debe}")
        self.stdout.write(f"   Total Haber: {total_haber}")
        self.stdout.write(f"   Nueva ubicación: {subarea_correcta.area.nombre} → {subarea_correcta.nombre}")
        
        self.stdout.write(self.style.SUCCESS("\n✅ RECLASIFICACIÓN COMPLETADA"))
        self.stdout.write("💡 Ahora ejecuta tu endpoint /estado-resultados/ para ver los cambios")
