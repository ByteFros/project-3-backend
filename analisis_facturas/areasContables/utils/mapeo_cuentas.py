# utils/mapeo_cuentas.py - Versión Consolidada
import re
from datetime import datetime, timedelta,date
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Union
from decimal import Decimal, InvalidOperation
from areasContables.models import SubAreaContable, AreaContable, SeccionContable


# ========================================
# CONSOLIDACIÓN DE FUNCIONES DE NORMALIZACIÓN
# ========================================

def normalizar_codigo_cuenta(codigo_cuenta: Any) -> str:
    """
    Normaliza códigos de cuenta manejando TODOS los formatos posibles.
    Consolidación mejorada de ambas funciones existentes.

    Ejemplos:
    - "100.0001" → "100"
    - "40000000022" → "400"
    - "6251" → "625" (si >3 dígitos, tomar primeros 3)
    - "23" → "23" (si ≤3 dígitos, mantener)
    """
    if not codigo_cuenta:
        return ""

    # Convertir a string y limpiar
    codigo_str = str(codigo_cuenta).strip()

    # Manejar valores vacíos o nulos
    if codigo_str.lower() in ['nan', 'nat', 'none', '', 'null']:
        return ""

    # CASO 1: Código con punto (formato "100.0001")
    if '.' in codigo_str:
        parte_principal = codigo_str.split('.')[0]
        # Eliminar caracteres no numéricos y devolver
        solo_numeros = re.sub(r'[^0-9]', '', parte_principal)
        return solo_numeros if solo_numeros else ""

    # CASO 2: Solo números, eliminar otros caracteres
    solo_numeros = re.sub(r'[^0-9]', '', codigo_str)

    if not solo_numeros:
        return ""

    # CASO 3: Códigos largos (>3 dígitos) - extraer grupo principal
    if len(solo_numeros) > 3:
        # Para códigos muy largos, tomar los primeros 3 dígitos
        return solo_numeros[:3]

    # CASO 4: Códigos cortos (≤3 dígitos) - mantener como están
    return solo_numeros


def extraer_patrones_cuenta(codigo_normalizado: str) -> List[str]:
    """
    Extrae patrones jerárquicos para búsqueda inteligente.
    Mejorado para manejar mejor los códigos de tu sistema.

    Ejemplos:
    - "400" → ["400", "40", "4"]
    - "6251" → ["625", "62", "6"] (ya normalizado)
    - "23" → ["23", "2"]
    """
    if not codigo_normalizado:
        return []

    patrones = [codigo_normalizado]  # Código completo

    # Generar patrones progresivamente más cortos
    for i in range(len(codigo_normalizado) - 1, 0, -1):
        patron = codigo_normalizado[:i]
        if patron and patron not in patrones:
            patrones.append(patron)

    return patrones


# ========================================
# CONSOLIDACIÓN DE FUNCIONES DE PARSING
# ========================================

def parse_decimal_mejorado(valor: Any) -> Optional[Decimal]:
    """
    Consolidación mejorada de parse_number() y _parse_decimal().
    Maneja todos los formatos de números posibles.
    """
    if valor is None or valor == '' or str(valor).strip() == '':
        return None

    # Si ya es un número
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    if isinstance(valor, Decimal):
        return valor

    # Procesar strings
    if isinstance(valor, str):
        # Limpiar el string
        cleaned = valor.strip().replace(' ', '').replace(',', '.')

        # Manejar separadores de miles múltiples
        parts = cleaned.split('.')
        if len(parts) > 2:
            # Todo menos el último punto son separadores de miles
            cleaned = ''.join(parts[:-1]) + '.' + parts[-1]

        try:
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            print(f"⚠️  Error parseando número: '{valor}'")
            return None

    return None


def parse_fecha_mejorada(fecha_valor: Any) -> Optional[datetime.date]:
    if not fecha_valor or (isinstance(fecha_valor, str) and fecha_valor.strip() == ""):
        return None

    try:
        # Si ya es fecha
        if isinstance(fecha_valor, (date, datetime, pd.Timestamp)):
            return fecha_valor.date()

        # Si es número (serial Excel)
        if isinstance(fecha_valor, (int, float)):
            if 1 <= fecha_valor <= 100000:
                excel_epoch = datetime(1900, 1, 1)
                days = int(fecha_valor) - 2
                return (excel_epoch + timedelta(days=days)).date()

        # Configurar localización a español para meses abreviados
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')  # Linux/Mac
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')  # Windows
            except:
                pass

        # Convertir a string
        fecha_str = str(fecha_valor).strip()
        if fecha_str.lower() in ['nan', 'nat', 'none', '', 'null']:
            return None

        formatos_fecha = [
            "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
            "%d/%m/%y", "%d-%m-%y", "%y/%m/%d", "%d.%m.%Y", "%d %m %Y", "%Y%m%d",
            "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d %b %y"  # español
        ]

        for formato in formatos_fecha:
            try:
                return datetime.strptime(fecha_str, formato).date()
            except ValueError:
                continue

        # Último intento: parse flexible
        try:
            from dateutil import parser
            return parser.parse(fecha_str, dayfirst=True).date()
        except:
            pass

    except Exception as e:
        print(f"❌ Error inesperado al parsear fecha '{fecha_valor}': {e}")

    print(f"⚠️  No se pudo parsear la fecha '{fecha_valor}' (tipo: {type(fecha_valor)})")
    return None


# ========================================
# CONSOLIDACIÓN DE MAPEO DE COLUMNAS
# ========================================

# Mapeo consolidado y ampliado de columnas
MAPEO_COLUMNAS_COMPLETO = {
    'fecha': [
        'fecha', 'Fecha', 'FECHA', 'Date','date', 'Fec', 'F'
    ],
    'asiento': [
        'asiento', 'Asiento', 'ASIENTO', 'Asto', 'asto', 'ASTO',
        'ref. int.', 'ref int', 'referencia interna', 'ref', 'referencia'
    ],
    'documento': [
        'documento', 'Documento', 'DOCUMENTO', 'Doc', 'doc', 'D',
        'apunte', 'Apunte', 'APUNTE'
    ],
    'cuenta': [
        'cuenta', 'Cuenta', 'CUENTA', 'Nº Cuenta', 'Cta', 'account',
        'Account', 'ACCOUNT', 'code', 'Code', 'codigo', 'Codigo'
    ],
    'nombre': [
        'nombre', 'Nombre', 'NOMBRE', 'Name', 'name', 'NAME',
        'descripcion', 'Descripcion', 'Descripción', 'DESCRIPCION',
        'descripción de la cuenta', 'Descripción de la cuenta',
        'desc cuenta', 'desc_cuenta', 'account_name', 'account name'
    ],
    'concepto': [
        'concepto', 'Concepto', 'CONCEPTO', 'Description', 'description',
        'DESCRIPTION', 'detalle', 'Detalle', 'DETALLE', 'detail'
    ],
    'debe': [
        'debe', 'Debe', 'DEBE', 'Debit', 'debit', 'DEBIT',
        'debito', 'Debito', 'Débito', 'importe debe', 'Importe debe',
        'importe_debe', 'debe_importe', 'valor_debe', 'monto_debe'
    ],
    'haber': [
        'haber', 'Haber', 'HABER', 'Credit', 'credit', 'CREDIT',
        'credito', 'Credito', 'Crédito', 'importe haber', 'Importe haber',
        'importe_haber', 'haber_importe', 'valor_haber', 'monto_haber'
    ]
}


def mapear_columnas_excel(encabezados: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Consolidación mejorada de mapeo de columnas.
    Combina funcionalidades de _mapear_columnas() y get_column_value().
    """
    # Convertir encabezados a minúsculas para búsqueda
    encabezados_limpios = []
    for h in encabezados:
        encabezados_limpios = []
        for h in encabezados:
            texto = str(h).lower()
            texto = re.sub(r'\s+', ' ', texto)  # reemplaza múltiples espacios por uno
            texto = texto.strip()
            encabezados_limpios.append(texto)

    mapeo_encontrado = {}

    # Para cada campo del sistema, buscar la mejor coincidencia
    for campo_sistema, posibles_nombres in MAPEO_COLUMNAS_COMPLETO.items():
        mejor_coincidencia = None
        mejor_indice = -1
        mejor_score = 0

        for i, encabezado in enumerate(encabezados_limpios):
            for nombre_posible in posibles_nombres:
                nombre_posible_lower = nombre_posible.lower()

                # Calcular score de coincidencia
                score = 0
                if encabezado == nombre_posible_lower:
                    score = 100  # Coincidencia exacta
                elif nombre_posible_lower in encabezado:
                    score = 80  # Contiene el término
                elif encabezado in nombre_posible_lower:
                    score = 60  # El término contiene el encabezado

                # Actualizar si es mejor coincidencia
                if score > mejor_score:
                    mejor_coincidencia = encabezados[i]  # Nombre original
                    mejor_indice = i
                    mejor_score = score

        if mejor_coincidencia:
            mapeo_encontrado[campo_sistema] = {
                'nombre_original': mejor_coincidencia,
                'indice': mejor_indice,
                'score': mejor_score,
                'nombre_normalizado': campo_sistema
            }

    return mapeo_encontrado


def obtener_valor_mapeado(fila_dict: Dict[str, Any], campo_sistema: str,
                          mapeo_columnas: Dict[str, Dict[str, Any]]) -> Any:
    """
    Obtiene el valor de una fila usando el mapeo de columnas.
    Versión consolidada y mejorada.
    """
    if campo_sistema not in mapeo_columnas:
        return None

    nombre_original = mapeo_columnas[campo_sistema]['nombre_original']
    valor = fila_dict.get(nombre_original)

    # Limpiar el valor si es string
    if isinstance(valor, str):
        valor = valor.strip()
        if valor == '' or valor.lower() in ['nan', 'nat', 'none', 'null']:
            return None

    return valor


# ========================================
# SISTEMA DE BÚSQUEDA DE SUBAREAS MEJORADO
# ========================================

def buscar_subarea_por_cuenta_mejorado(codigo_cuenta_original: str) -> Optional[SubAreaContable]:
    """
    Versión mejorada del sistema de búsqueda de subareas.
    Integra toda la lógica de ambos archivos con mejoras adicionales.
    """
    if not codigo_cuenta_original:
        return None

    # 1. Normalizar el código
    codigo_normalizado = normalizar_codigo_cuenta(codigo_cuenta_original)

    if not codigo_normalizado:
        return None

    # 2. Generar patrones de búsqueda jerárquicos
    patrones_busqueda = extraer_patrones_cuenta(codigo_normalizado)

    # 3. Buscar en la base de datos con sistema de prioridades
    mejores_coincidencias = []

    try:
        subareas = SubAreaContable.objects.all()

        for subarea in subareas:
            # Buscar en códigos positivos
            for codigo_positivo in subarea.codigos_pos_list():
                codigo_pos_str = str(codigo_positivo)

                for i, patron in enumerate(patrones_busqueda):
                    coincidencia = calcular_coincidencia(patron, codigo_pos_str)

                    if coincidencia['score'] > 0:
                        prioridad = coincidencia['score'] + (100 - i * 10)  # Bonus por patrón más específico

                        mejores_coincidencias.append({
                            'subarea': subarea,
                            'tipo': 'positivo',
                            'codigo_db': codigo_positivo,
                            'patron_usado': patron,
                            'prioridad': prioridad,
                            'score': coincidencia['score'],
                            'tipo_coincidencia': coincidencia['tipo']
                        })

            # Buscar en códigos negativos (con menor prioridad)
            for codigo_negativo in subarea.codigos_neg_list():
                codigo_neg_str = str(codigo_negativo)

                for i, patron in enumerate(patrones_busqueda):
                    coincidencia = calcular_coincidencia(patron, codigo_neg_str)

                    if coincidencia['score'] > 0:
                        prioridad = (coincidencia['score'] // 2) + (50 - i * 5)  # Menor prioridad

                        mejores_coincidencias.append({
                            'subarea': subarea,
                            'tipo': 'negativo',
                            'codigo_db': codigo_negativo,
                            'patron_usado': patron,
                            'prioridad': prioridad,
                            'score': coincidencia['score'],
                            'tipo_coincidencia': coincidencia['tipo']
                        })

    except Exception as e:
        print(f"❌ Error al buscar en BD: {e}")
        pass

    # 4. Evaluar coincidencias y devolver la mejor
    if mejores_coincidencias:
        # Ordenar por prioridad (mayor prioridad primero)
        mejores_coincidencias.sort(key=lambda x: x['prioridad'], reverse=True)
        mejor = mejores_coincidencias[0]

        # Debug logging mejorado
        print(f"✅ CUENTA MAPEADA: '{codigo_cuenta_original}' → '{mejor['subarea'].nombre}' "
              f"(Código DB: {mejor['codigo_db']}, Tipo: {mejor['tipo']}, "
              f"Prioridad: {mejor['prioridad']}, Score: {mejor['score']}, "
              f"Coincidencia: {mejor['tipo_coincidencia']})")

        return mejor['subarea']

    # 5. Fallback: buscar en códigos BOE hardcodeados
    subarea_boe = buscar_en_codigos_boe_mejorado(codigo_cuenta_original)
    if subarea_boe:
        return subarea_boe

    # 6. No se encontró coincidencia
    print(f"❌ CUENTA NO ENCONTRADA: '{codigo_cuenta_original}' "
          f"(normalizada: '{codigo_normalizado}', patrones: {patrones_busqueda})")

    return None


def calcular_coincidencia(patron: str, codigo_db: str) -> Dict[str, Any]:
    """
    Calcula el score de coincidencia entre un patrón y un código de BD.
    """
    if patron == codigo_db:
        return {'score': 100, 'tipo': 'exacta'}

    if patron.startswith(codigo_db):
        return {'score': 90, 'tipo': 'contiene_db'}

    if codigo_db.startswith(patron):
        return {'score': 80, 'tipo': 'contiene_patron'}

    # Coincidencia parcial por longitud común
    longitud_comun = 0
    for i, (c1, c2) in enumerate(zip(patron, codigo_db)):
        if c1 == c2:
            longitud_comun += 1
        else:
            break

    if longitud_comun >= 2:  # Al menos 2 dígitos coinciden
        score = 30 + (longitud_comun * 10)
        return {'score': score, 'tipo': f'parcial_{longitud_comun}'}

    return {'score': 0, 'tipo': 'ninguna'}


def buscar_en_codigos_boe_mejorado(codigo_cuenta_original: str) -> Optional[SubAreaContable]:
    """
    Versión mejorada de búsqueda en códigos BOE.
    """
    from .codigos_boe import ACTIVO_NO_CORRIENTE, ACTIVO_CORRIENTE

    codigo_normalizado = normalizar_codigo_cuenta(codigo_cuenta_original)
    patrones_busqueda = extraer_patrones_cuenta(codigo_normalizado)

    # Buscar en ambas estructuras BOE
    estructuras = [
        (ACTIVO_NO_CORRIENTE, "ACTIVO NO CORRIENTE"),
        (ACTIVO_CORRIENTE, "ACTIVO CORRIENTE")
    ]

    for estructura, nombre_estructura in estructuras:
        for area_nombre, area_data in estructura.items():
            for subarea_nombre, subarea_data in area_data['subareas'].items():

                # Verificar códigos a sumar
                for codigo_str in subarea_data['sumar']:
                    for patron in patrones_busqueda:
                        if patron == codigo_str or patron.startswith(codigo_str):
                            print(f"🔍 BOE MATCH ({nombre_estructura}): '{codigo_cuenta_original}' → "
                                  f"{area_nombre} - {subarea_nombre} (Código: {codigo_str})")
                            return buscar_o_crear_subarea_boe(area_nombre, subarea_nombre)

                # Verificar códigos a restar (menor prioridad)
                for codigo_str in subarea_data['restar']:
                    for patron in patrones_busqueda:
                        if patron == codigo_str or patron.startswith(codigo_str):
                            print(f"🔍 BOE MATCH ({nombre_estructura} - RESTAR): '{codigo_cuenta_original}' → "
                                  f"{area_nombre} - {subarea_nombre} (Código: {codigo_str})")
                            return buscar_o_crear_subarea_boe(area_nombre, subarea_nombre)

    return None


def buscar_o_crear_subarea_boe(area_nombre: str, subarea_nombre: str) -> Optional[SubAreaContable]:
    """
    Busca una subarea basada en los datos BOE.
    NO crea nuevas subareas como solicitaste.
    """
    try:
        # Intentar encontrar el área existente por nombre similar
        area = AreaContable.objects.filter(nombre__icontains=area_nombre).first()

        if not area:
            # Buscar por palabras clave
            palabras_clave = area_nombre.lower().split()
            for palabra in palabras_clave:
                if len(palabra) > 3:  # Solo palabras significativas
                    area = AreaContable.objects.filter(nombre__icontains=palabra).first()
                    if area:
                        break

        if not area:
            print(f"⚠️  Área '{area_nombre}' no encontrada en BD")
            return None

        # Buscar la subarea en el área encontrada
        subarea = SubAreaContable.objects.filter(
            area=area,
            nombre__icontains=subarea_nombre
        ).first()

        if not subarea:
            # Buscar por palabras clave en subarea
            palabras_clave = subarea_nombre.lower().split()
            for palabra in palabras_clave:
                if len(palabra) > 3:
                    subarea = SubAreaContable.objects.filter(
                        area=area,
                        nombre__icontains=palabra
                    ).first()
                    if subarea:
                        break

        if subarea:
            print(f"✅ SubArea BOE encontrada: {subarea.nombre} (Área: {area.nombre})")
            return subarea
        else:
            print(f"⚠️  SubArea '{subarea_nombre}' no encontrada en área '{area.nombre}'")
            return None

    except Exception as e:
        print(f"❌ Error al buscar subarea BOE: {e}")
        return None


# ========================================
# FUNCIONES DE ANÁLISIS Y ESTADÍSTICAS
# ========================================

def analizar_mapeo_cuentas_completo(cuentas_archivo: List[str]) -> Dict[str, Any]:
    """
    Análisis completo del mapeo de cuentas con estadísticas detalladas.
    """
    resultado = {
        'cuentas_mapeadas': [],
        'cuentas_no_mapeadas': [],
        'estadisticas_detalladas': {},
        'recomendaciones': []
    }

    contadores = {
        'exactas': 0,
        'parciales': 0,
        'boe': 0,
        'no_encontradas': 0
    }

    for cuenta in cuentas_archivo:
        subarea = buscar_subarea_por_cuenta_mejorado(cuenta)

        if subarea:
            resultado['cuentas_mapeadas'].append({
                'cuenta_original': cuenta,
                'cuenta_normalizada': normalizar_codigo_cuenta(cuenta),
                'subarea': subarea.nombre,
                'area': subarea.area.nombre if hasattr(subarea, 'area') else 'N/A',
                'seccion': subarea.area.seccion.nombre if hasattr(subarea.area, 'seccion') else 'N/A'
            })
            contadores['exactas'] += 1
        else:
            cuenta_normalizada = normalizar_codigo_cuenta(cuenta)
            resultado['cuentas_no_mapeadas'].append({
                'cuenta_original': cuenta,
                'cuenta_normalizada': cuenta_normalizada,
                'grupo_detectado': cuenta_normalizada[:2] if len(cuenta_normalizada) >= 2 else cuenta_normalizada,
                'clase_detectada': cuenta_normalizada[:1] if cuenta_normalizada else 'N/A'
            })
            contadores['no_encontradas'] += 1

    # Calcular estadísticas
    total = len(cuentas_archivo)
    resultado['estadisticas_detalladas'] = {
        'total_cuentas': total,
        'mapeadas': len(resultado['cuentas_mapeadas']),
        'no_mapeadas': len(resultado['cuentas_no_mapeadas']),
        'porcentaje_exito': (len(resultado['cuentas_mapeadas']) / total * 100) if total > 0 else 0,
        'contadores_tipo': contadores
    }

    # Generar recomendaciones
    if resultado['cuentas_no_mapeadas']:
        grupos_no_mapeados = {}
        for cuenta in resultado['cuentas_no_mapeadas']:
            grupo = cuenta['grupo_detectado']
            if grupo not in grupos_no_mapeados:
                grupos_no_mapeados[grupo] = 0
            grupos_no_mapeados[grupo] += 1

        for grupo, cantidad in sorted(grupos_no_mapeados.items(), key=lambda x: x[1], reverse=True):
            if cantidad > 5:  # Solo grupos con muchas cuentas
                resultado['recomendaciones'].append({
                    'tipo': 'crear_subarea',
                    'grupo': grupo,
                    'cantidad_cuentas': cantidad,
                    'descripcion': f"Considerar crear subarea para grupo {grupo} ({cantidad} cuentas no mapeadas)"
                })

    return resultado


# ========================================
# FUNCIÓN PRINCIPAL PÚBLICA
# ========================================

# Alias para mantener compatibilidad con código existente
buscar_subarea_por_cuenta = buscar_subarea_por_cuenta_mejorado


# Función principal para usar en FacturaUploadView
def procesar_fila_excel(fila_dict: Dict[str, Any], mapeo_columnas: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Procesa una fila del Excel usando toda la funcionalidad consolidada.

    Returns:
        Dict con datos normalizados y listos para crear LineaFactura
    """
    # Extraer valores usando mapeo
    fecha_valor = obtener_valor_mapeado(fila_dict, 'fecha', mapeo_columnas)
    asiento = obtener_valor_mapeado(fila_dict, 'asiento', mapeo_columnas) or ""
    documento = obtener_valor_mapeado(fila_dict, 'documento', mapeo_columnas) or ""
    cuenta_original = obtener_valor_mapeado(fila_dict, 'cuenta', mapeo_columnas) or ""
    nombre = obtener_valor_mapeado(fila_dict, 'nombre', mapeo_columnas) or ""
    concepto = obtener_valor_mapeado(fila_dict, 'concepto', mapeo_columnas) or ""
    debe_original = obtener_valor_mapeado(fila_dict, 'debe', mapeo_columnas)
    haber_original = obtener_valor_mapeado(fila_dict, 'haber', mapeo_columnas)

    # Procesar y normalizar valores
    fecha_formateada = parse_fecha_mejorada(fecha_valor)
    cuenta_normalizada = normalizar_codigo_cuenta(cuenta_original)
    debe = parse_decimal_mejorado(debe_original)
    haber = parse_decimal_mejorado(haber_original)

    # Buscar subarea
    subarea = buscar_subarea_por_cuenta_mejorado(cuenta_original)

    # Validaciones
    problemas = []
    if not cuenta_normalizada:
        problemas.append("cuenta_vacia")
    if not debe and not haber:
        problemas.append("sin_valores_monetarios")
    if not subarea:
        problemas.append("sin_subarea")
    if not fecha_formateada:
        problemas.append("fecha_invalida")

    return {
        'datos_procesados': {
            'fecha': fecha_formateada,
            'asiento': asiento,
            'documento': documento,
            'cuenta': cuenta_original,
            'cuenta_normalizada': cuenta_normalizada,
            'nombre': nombre,
            'concepto': concepto,
            'debe': debe,
            'haber': haber,
            'subarea': subarea
        },
        'valores_originales': {
            'fecha_original': fecha_valor,
            'debe_original': debe_original,
            'haber_original': haber_original
        },
        'validaciones': {
            'es_valida': len(problemas) == 0,
            'problemas': problemas,
            'tiene_subarea': subarea is not None,
            'tiene_valores': (debe and debe > 0) or (haber and haber > 0)
        }
    }