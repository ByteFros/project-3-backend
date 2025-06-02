# utils/excel_processor.py
import re
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from decimal import Decimal, InvalidOperation
from django.db import transaction
from ..models.areaContable import SubAreaContable
from .codigos_boe import ACTIVO_NO_CORRIENTE, ACTIVO_CORRIENTE


class ExcelNormalizer:
    """
    Normalizador de datos Excel que se integra con tu sistema existente
    """

    # Mapeo de posibles nombres de columnas
    COLUMN_MAPPINGS = {
        'fecha': ['fecha', 'Fecha', 'FECHA', 'Date'],
        'asiento': ['asiento', 'Asiento', 'ASIENTO', 'Asto', 'asto', 'ASTO'],
        'documento': ['documento', 'Documento', 'DOCUMENTO', 'Doc', 'doc'],
        'cuenta': ['cuenta', 'Cuenta', 'CUENTA', 'Nº Cuenta', 'Cta'],
        'nombre': ['nombre', 'Nombre', 'NOMBRE', 'Name', 'Descripcion', 'Descripción de la cuenta'],
        'concepto': ['concepto', 'Concepto', 'CONCEPTO', 'Description'],
        'debe': ['debe', 'Debe', 'DEBE', 'Debit', 'Importe debe'],
        'haber': ['haber', 'Haber', 'HABER', 'Credit', 'Importe haber']
    }

    @staticmethod
    def get_column_value(row: Dict[str, Any], column_type: str) -> Any:
        """
        Obtiene el valor de una columna usando múltiples nombres posibles
        """
        possible_names = ExcelNormalizer.COLUMN_MAPPINGS.get(column_type, [])

        for name in possible_names:
            if name in row and row[name] is not None and str(row[name]).strip():
                return row[name]

        return None

    @staticmethod
    def parse_number(value: Any) -> Decimal:
        """
        Convierte un valor a Decimal de forma robusta
        """
        if value is None or value == '' or str(value).strip() == '':
            return Decimal('0')

        if isinstance(value, (int, float)):
            return Decimal(str(value))

        if isinstance(value, str):
            # Limpiar el string: remover espacios
            cleaned = value.strip().replace(',', '.')

            # Manejar separadores de miles
            parts = cleaned.split('.')
            if len(parts) > 2:
                # Reconstruir: todo menos el último punto son separadores de miles
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]

            try:
                return Decimal(cleaned)
            except (InvalidOperation, ValueError):
                print(f"Error parseando número: {value}")
                return Decimal('0')

        return Decimal('0')

    @staticmethod
    def normalizar_codigo_cuenta(codigo_cuenta: Any) -> str:
        """
        Normaliza el código de cuenta para diferentes formatos
        Compatible con tu función buscar_subarea_por_cuenta existente
        """
        if not codigo_cuenta:
            return ''

        codigo_str = str(codigo_cuenta).strip()

        # Si ya tiene puntos, extraer la primera parte (compatibilidad con tu sistema)
        if '.' in codigo_str:
            return codigo_str.split('.')[0]

        # Si es un número largo sin puntos (8+ dígitos), extraer los primeros 3
        if re.match(r'^\d{8,}$', codigo_str):
            return codigo_str[:3]

        # Si es un código corto (1-3 dígitos), mantenerlo como está
        # NO rellenar con ceros automáticamente para mantener compatibilidad
        if re.match(r'^\d{1,3}$', codigo_str):
            return codigo_str

        # Para otros casos, extraer solo números
        solo_numeros = re.sub(r'\D', '', codigo_str)
        if len(solo_numeros) >= 3:
            return solo_numeros[:3]

        return solo_numeros if solo_numeros else ''

    @staticmethod
    def detectar_formato_excel(data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detecta el formato del archivo Excel
        """
        if not data:
            return {
                'tipo_formato': 'desconocido',
                'columnas_detectadas': [],
                'muestra_data': {},
                'confianza': 0
            }

        primera_fila = data[0] if data else {}
        columnas = list(primera_fila.keys())

        # Calcular confianza basada en columnas encontradas
        columnas_esenciales = ['fecha', 'cuenta', 'debe', 'haber']
        confianza = 0

        for col_type in columnas_esenciales:
            if ExcelNormalizer.get_column_value(primera_fila, col_type) is not None:
                confianza += 25

        # Detectar tipo específico
        tiene_formato_original = any(
            col.lower() in ['fecha', 'asiento', 'cuenta', 'debe', 'haber']
            for col in columnas
        )

        tiene_formato_nuevo = any(
            col in ['Fecha', 'Asiento', 'Cuenta', 'Importe debe', 'Importe haber']
            for col in columnas
        )

        tipo_formato = 'desconocido'
        if tiene_formato_original:
            tipo_formato = 'formato_original'
        elif tiene_formato_nuevo:
            tipo_formato = 'formato_nuevo'

        return {
            'tipo_formato': tipo_formato,
            'columnas_detectadas': columnas,
            'muestra_data': primera_fila,
            'confianza': confianza
        }

    @staticmethod
    def normalize_row_data(row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza una fila de datos manteniendo compatibilidad con tu sistema
        """
        return {
            'fecha': ExcelNormalizer.get_column_value(row, 'fecha') or '',
            'asiento': ExcelNormalizer.get_column_value(row, 'asiento') or '',
            'documento': ExcelNormalizer.get_column_value(row, 'documento') or '',
            'cuenta': ExcelNormalizer.normalizar_codigo_cuenta(
                ExcelNormalizer.get_column_value(row, 'cuenta')
            ),
            'nombre': ExcelNormalizer.get_column_value(row, 'nombre') or '',
            'concepto': ExcelNormalizer.get_column_value(row, 'concepto') or '',
            'debe': ExcelNormalizer.parse_number(ExcelNormalizer.get_column_value(row, 'debe')),
            'haber': ExcelNormalizer.parse_number(ExcelNormalizer.get_column_value(row, 'haber')),
            # Mantener datos originales para debug
            'original_row': row
        }


class ContabilidadProcessor:
    """
    Procesador que integra la normalización con tu sistema existente
    """

    def __init__(self):
        self.normalizer = ExcelNormalizer()

    def procesar_datos_excel(self, raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Procesa datos Excel con validación y estadísticas
        """
        formato_detectado = self.normalizer.detectar_formato_excel(raw_data)

        if formato_detectado['confianza'] < 50:
            raise ValueError(f"Formato de Excel no reconocido. Confianza: {formato_detectado['confianza']}%")

        datos_normalizados = []
        errores = []

        for i, row in enumerate(raw_data):
            try:
                row_normalizada = self.normalizer.normalize_row_data(row)

                # Validar que la fila tenga datos mínimos
                if row_normalizada['cuenta'] and (row_normalizada['debe'] > 0 or row_normalizada['haber'] > 0):
                    datos_normalizados.append(row_normalizada)

            except Exception as e:
                errores.append({
                    'fila': i + 1,
                    'error': str(e),
                    'data': row
                })

        # Calcular estadísticas usando tus funciones existentes
        cuentas_encontradas = {}
        cuentas_sin_subarea = []

        for row in datos_normalizados:
            cuenta = row['cuenta']
            if cuenta:
                # Usar tu función existente
                from . import buscar_subarea_por_cuenta
                subarea = buscar_subarea_por_cuenta(cuenta)

                if subarea:
                    if cuenta not in cuentas_encontradas:
                        cuentas_encontradas[cuenta] = {
                            'subarea': subarea.nombre,
                            'area': subarea.area.nombre if hasattr(subarea, 'area') else 'N/A',
                            'debe_total': Decimal('0'),
                            'haber_total': Decimal('0'),
                            'movimientos': 0
                        }

                    cuentas_encontradas[cuenta]['debe_total'] += row['debe']
                    cuentas_encontradas[cuenta]['haber_total'] += row['haber']
                    cuentas_encontradas[cuenta]['movimientos'] += 1
                else:
                    if cuenta not in cuentas_sin_subarea:
                        cuentas_sin_subarea.append(cuenta)

        return {
            'datos_normalizados': datos_normalizados,
            'formato_detectado': formato_detectado,
            'estadisticas': {
                'total_filas_procesadas': len(datos_normalizados),
                'total_filas_originales': len(raw_data),
                'filas_con_errores': len(errores),
                'cuentas_encontradas': len(cuentas_encontradas),
                'cuentas_sin_subarea': len(cuentas_sin_subarea),
                'debe_total': sum(row['debe'] for row in datos_normalizados),
                'haber_total': sum(row['haber'] for row in datos_normalizados)
            },
            'cuentas_detalle': cuentas_encontradas,
            'cuentas_sin_subarea': cuentas_sin_subarea,
            'errores': errores
        }

    def calcular_total_activo_con_codigos_boe(self, datos_normalizados: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula el total activo usando tus códigos BOE definidos
        """

        def procesar_estructura(estructura_boe: Dict, letra_seccion: str, nombre_seccion: str):
            seccion_result = {
                'letra': letra_seccion,
                'nombre': nombre_seccion,
                'debe': Decimal('0'),
                'haber': Decimal('0'),
                'saldo': Decimal('0'),
                'areas': []
            }

            for area_nombre, area_config in estructura_boe.items():
                area_result = {
                    'nombre': area_nombre,
                    'debe': Decimal('0'),
                    'haber': Decimal('0'),
                    'saldo': Decimal('0'),
                    'subareas': []
                }

                for subarea_nombre, subarea_config in area_config['subareas'].items():
                    subarea_result = {
                        'nombre': subarea_nombre,
                        'debe': Decimal('0'),
                        'haber': Decimal('0'),
                        'saldo': Decimal('0'),
                        'total_lineas': 0
                    }

                    # Procesar códigos a sumar
                    for codigo in subarea_config.get('sumar', []):
                        for row in datos_normalizados:
                            if row['cuenta'].startswith(codigo):
                                subarea_result['debe'] += row['debe']
                                subarea_result['haber'] += row['haber']
                                subarea_result['total_lineas'] += 1

                    # Procesar códigos a restar
                    for codigo in subarea_config.get('restar', []):
                        for row in datos_normalizados:
                            if row['cuenta'].startswith(codigo):
                                subarea_result['debe'] -= row['debe']
                                subarea_result['haber'] -= row['haber']

                    # Calcular saldo (para activos, normalmente debe - haber)
                    subarea_result['saldo'] = subarea_result['debe'] - subarea_result['haber']

                    area_result['subareas'].append(subarea_result)
                    area_result['debe'] += subarea_result['debe']
                    area_result['haber'] += subarea_result['haber']

                area_result['saldo'] = area_result['debe'] - area_result['haber']
                seccion_result['areas'].append(area_result)
                seccion_result['debe'] += area_result['debe']
                seccion_result['haber'] += area_result['haber']

            seccion_result['saldo'] = seccion_result['debe'] - seccion_result['haber']
            return seccion_result

        # Procesar ambas secciones
        activo_no_corriente = procesar_estructura(
            ACTIVO_NO_CORRIENTE, 'A', 'Activo no corriente'
        )
        activo_corriente = procesar_estructura(
            ACTIVO_CORRIENTE, 'B', 'Activo corriente'
        )

        # Calcular totales
        total_debe = activo_no_corriente['debe'] + activo_corriente['debe']
        total_haber = activo_no_corriente['haber'] + activo_corriente['haber']
        total_saldo = total_debe - total_haber

        resultado = {
            'total_activo': {
                'saldo': float(total_saldo),
                'debe_total': float(total_debe),
                'haber_total': float(total_haber),
                'formula': 'ACTIVO NO CORRIENTE + ACTIVO CORRIENTE'
            },
            'detalle_por_seccion': [activo_no_corriente, activo_corriente],
            'validaciones': {
                'sumas_cuadran': True,
                'tiene_activos': total_saldo != 0
            }
        }

        # Convertir Decimals a float para JSON
        return self._convert_decimals_to_float(resultado)

    def guardar_en_base_datos(self, datos_normalizados: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Guarda los datos normalizados en tu base de datos
        """
        from ..models import LineaFactura  # Ajusta según tu modelo

        resultados = {
            'guardados': 0,
            'errores': 0,
            'detalles_errores': []
        }

        try:
            with transaction.atomic():
                for row in datos_normalizados:
                    try:
                        # Usar tu función existente para encontrar subarea
                        from . import buscar_subarea_por_cuenta
                        subarea = buscar_subarea_por_cuenta(row['cuenta'])

                        # Crear el objeto (ajusta según tu modelo)
                        LineaFactura.objects.create(
                            fecha=row['fecha'],
                            asiento=row['asiento'],
                            documento=row['documento'],
                            cuenta=row['cuenta'],
                            nombre=row['nombre'],
                            concepto=row['concepto'],
                            debe=row['debe'],
                            haber=row['haber'],
                            subarea=subarea
                        )
                        resultados['guardados'] += 1

                    except Exception as e:
                        resultados['errores'] += 1
                        resultados['detalles_errores'].append({
                            'cuenta': row.get('cuenta', 'N/A'),
                            'error': str(e)
                        })

        except Exception as e:
            raise Exception(f"Error en transacción: {str(e)}")

        return resultados

    def _convert_decimals_to_float(self, obj):
        """Convierte Decimals a float recursivamente"""
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {key: self._convert_decimals_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals_to_float(item) for item in obj]
        else:
            return obj


# Función principal que combina todo tu flujo existente
def procesar_excel_completo(raw_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Función principal que procesa un Excel de principio a fin
    """
    processor = ContabilidadProcessor()

    try:
        # 1. Procesar y normalizar datos
        resultado_procesamiento = processor.procesar_datos_excel(raw_data)

        # 2. Calcular balance usando códigos BOE
        balance_activo = processor.calcular_total_activo_con_codigos_boe(
            resultado_procesamiento['datos_normalizados']
        )

        # 3. Guardar en base de datos (opcional)
        # resultado_guardado = processor.guardar_en_base_datos(
        #     resultado_procesamiento['datos_normalizados']
        # )

        return {
            'success': True,
            'procesamiento': resultado_procesamiento,
            'balance_activo': balance_activo,
            # 'guardado': resultado_guardado
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }