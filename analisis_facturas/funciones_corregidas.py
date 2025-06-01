# Reemplazo CORREGIDO para las funciones de clasificación
# Sustituir en la clase EstadoResultadosCorregidoView

def _es_ingreso_explotacion(self, area_nombre, subarea_nombre):
    """Identifica si es un ingreso de explotación"""
    # Patrones específicos basados en TUS datos reales
    if 'importe neto de la cifra de negocios' in area_nombre:
        return True
    if 'otros ingresos de explotación' in area_nombre:
        return True
    if area_nombre == 'ingresos y gastos' and subarea_nombre == 'ingresos':
        return True
    if area_nombre == 'ingresos' and 'extraordinario' not in subarea_nombre:
        return True
    return False

def _es_gasto_explotacion(self, area_nombre, subarea_nombre):
    """Identifica si es un gasto de explotación"""
    # Patrones específicos basados en TUS datos reales
    if area_nombre == 'ingresos y gastos' and subarea_nombre == 'gastos':
        return True
    if area_nombre == 'gastos':  # El área "Gastos" completa
        return True
    if 'amortizaciones' in area_nombre:
        return True
    if 'gastos de personal' in area_nombre:
        return True
    if 'otros gastos de explotación' in area_nombre:
        return True
    if 'aprovisionamientos' in area_nombre:
        return True
    return False

def _es_ingreso_financiero(self, area_nombre, subarea_nombre):
    """Identifica si es un ingreso financiero"""
    return 'ingresos financieros' in area_nombre

def _es_gasto_financiero(self, area_nombre, subarea_nombre):
    """Identifica si es un gasto financiero"""
    return 'gastos financieros' in area_nombre

def _es_ingreso_extraordinario(self, area_nombre, subarea_nombre):
    """Identifica si es un ingreso extraordinario"""
    if 'extraordinario' in subarea_nombre:
        return True
    if 'diferencias positivas de cambio' in subarea_nombre:
        return True
    return False

def _es_gasto_extraordinario(self, area_nombre, subarea_nombre):
    """Identifica si es un gasto extraordinario"""
    if 'extraordinario' in subarea_nombre and 'ingreso' not in subarea_nombre:
        return True
    if 'diferencias negativas de cambio' in subarea_nombre:
        return True
    return False

def _es_impuesto_beneficios(self, area_nombre, subarea_nombre):
    """Identifica si son impuestos sobre beneficios"""
    return 'impuestos sobre beneficios' in area_nombre
