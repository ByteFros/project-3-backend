#!/usr/bin/env python
"""
Script para debuggear específicamente el área 105 (Ingresos financieros)
Ejecutar con: python manage.py shell < debug_area_105.py
"""

from areasContables.models import AreaContable, LineaFactura
from decimal import Decimal

def debug_area_105():
    print("=== DEBUG ÁREA 105 (Ingresos financieros) ===")
    
    area_105 = AreaContable.objects.get(id=105)
    print(f"Área: {area_105.nombre}")
    
    total_esperado = Decimal('0')
    total_endpoint = Decimal('0')
    
    for subarea in area_105.subareas.all():
        print(f"\n--- Subárea: {subarea.nombre} ---")
        print(f"Códigos positivos: {subarea.codigos_positivos}")
        print(f"Códigos negativos: {subarea.codigos_negativos}")
        
        # Método del script de verificación (esperado)
        if subarea.codigos_positivos:
            codigos_pos = [c.strip() for c in subarea.codigos_positivos.split(',') if c.strip()]
            for i, codigo in enumerate(codigos_pos):
                valor = Decimal(f"10500.{i + 1:02d}")
                total_esperado += valor
                print(f"  ESPERADO - Código {codigo}: +{valor}")
        
        # Método del endpoint (real)
        if subarea.codigos_positivos:
            codigos_pos = [c.strip() for c in subarea.codigos_positivos.split(',') if c.strip()]
            for codigo in codigos_pos:
                # Simular exactamente lo que hace el endpoint
                lineas = LineaFactura.objects.filter(subarea=subarea, cuenta__startswith=codigo)
                print(f"  ENDPOINT - Código {codigo}: {lineas.count()} líneas encontradas")
                
                for linea in lineas:
                    debe = linea.debe or Decimal(0)
                    haber = linea.haber or Decimal(0)
                    
                    # Lógica del endpoint: para ingresos, suma el haber
                    if codigo.startswith('7'):  # Es cuenta de ingreso
                        valor_agregado = haber
                    else:
                        valor_agregado = debe
                    
                    total_endpoint += valor_agregado
                    print(f"    Línea: Concepto='{linea.concepto[:50]}...'")
                    print(f"           Debe={debe}, Haber={haber}")
                    print(f"           Agregando: {valor_agregado}")
    
    print(f"\n=== TOTALES ÁREA 105 ===")
    print(f"Esperado (script): {total_esperado}")
    print(f"Endpoint (real):   {total_endpoint}")
    print(f"Diferencia:        {abs(total_esperado - total_endpoint)}")
    
    # También verificar si hay líneas de prueba duplicadas o mezcladas
    todas_lineas_105 = LineaFactura.objects.filter(subarea__area=area_105)
    lineas_prueba = todas_lineas_105.filter(concepto__startswith="PRUEBA BOE")
    lineas_otras = todas_lineas_105.exclude(concepto__startswith="PRUEBA BOE")
    
    print(f"\n=== ANÁLISIS DE LÍNEAS ===")
    print(f"Total líneas en área 105: {todas_lineas_105.count()}")
    print(f"Líneas de prueba BOE: {lineas_prueba.count()}")
    print(f"Otras líneas: {lineas_otras.count()}")
    
    if lineas_otras.count() > 0:
        print("\n⚠️ HAY LÍNEAS NO DE PRUEBA:")
        for linea in lineas_otras[:5]:  # Mostrar solo las primeras 5
            print(f"  - Cuenta: {linea.cuenta}, Concepto: {linea.concepto[:30]}...")

debug_area_105()
