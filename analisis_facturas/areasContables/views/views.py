from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination

from ..models import LineaFactura
from ..serializers.serializers import LineaFacturaSerializer, LineaFacturaSimpleSerializer
import pandas as pd
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from areasContables.utils.mapeo_cuentas import (
    mapear_columnas_excel,
    procesar_fila_excel,
    analizar_mapeo_cuentas_completo,
    normalizar_codigo_cuenta,
    parse_fecha_mejorada,
    parse_decimal_mejorado
)


class FacturaUploadView(APIView):
    parser_classes = [MultiPartParser]

    def _detectar_tipo_archivo(self, archivo):
        """Detecta el tipo de archivo basado en la extensión"""
        nombre = archivo.name.lower()
        if nombre.endswith('.xls'):
            return 'xls'
        elif nombre.endswith('.xlsx'):
            return 'xlsx'
        elif nombre.endswith('.ods'):
            return 'ods'
        else:
            return 'desconocido'

    def _detectar_fila_encabezados(self, df):
        """
        Detecta automáticamente en qué fila están los encabezados reales
        Versión mejorada con más palabras clave
        """
        palabras_clave = [
            'fecha', 'asiento', 'cuenta', 'debe', 'haber', 'concepto', 'documento',
            'date', 'account', 'debit', 'credit', 'ref', 'importe', 'descripcion',
            'asto', 'doc', 'nombre', 'cta'
        ]

        # Buscar en las primeras 10 filas
        for fila_idx in range(min(10, len(df))):
            fila_valores = [str(val).strip().lower() for val in df.iloc[fila_idx].values if pd.notna(val)]

            # Contar cuántas palabras clave encontramos
            coincidencias = sum(1 for palabra in palabras_clave
                                if any(palabra in str(val) for val in fila_valores))

            # Si encontramos al menos 3 palabras clave, probablemente es la fila correcta
            if coincidencias >= 3:
                print(f"🎯 Encabezados detectados en fila {fila_idx + 1}: {df.iloc[fila_idx].values}")
                return fila_idx

        print("⚠️  No se detectaron encabezados automáticamente, usando fila 1")
        return 0

    def _leer_archivo_excel(self, archivo):
        """Lee archivos Excel (.xls y .xlsx) usando pandas"""
        try:
            # Primero leer sin encabezados para detectar la estructura
            df_temp = pd.read_excel(archivo, header=None,
                                    engine='openpyxl' if archivo.name.endswith('.xlsx') else 'xlrd')

            # Detectar fila de encabezados
            fila_encabezados = self._detectar_fila_encabezados(df_temp)

            # Leer el archivo con los encabezados correctos
            df = pd.read_excel(
                archivo,
                header=fila_encabezados,
                engine='openpyxl' if archivo.name.endswith('.xlsx') else 'xlrd',
                date_parser=None,
                keep_default_na=False,
            )

            # Limpiar nombres de columnas
            df.columns = [str(col).strip() if pd.notna(col) else f"Columna_{i}"
                          for i, col in enumerate(df.columns)]

            # Eliminar filas completamente vacías
            df = df.dropna(how='all')

            # Convertir DataFrame a formato de diccionarios
            encabezados = df.columns.tolist()
            filas = []

            for index, row in df.iterrows():
                valores = [str(val).strip() if pd.notna(val) else "" for val in row.values]
                # Solo incluir filas que tengan al menos una celda con contenido
                if any(val.strip() for val in valores):
                    fila_dict = dict(zip(encabezados, valores))
                    filas.append(fila_dict)

            return encabezados, filas

        except Exception as e:
            raise Exception(f"Error al leer archivo Excel: {str(e)}")

    def _leer_archivo_ods(self, archivo):
        """Lee archivos ODS usando la librería original"""
        try:
            from odf.opendocument import load
            from odf.table import Table, TableRow, TableCell
            from odf.text import P

            doc = load(archivo)
            hoja = doc.spreadsheet.getElementsByType(Table)[0]

            encabezados = []
            filas = []

            for i, row in enumerate(hoja.getElementsByType(TableRow)):
                celdas = row.getElementsByType(TableCell)
                valores = []

                for cell in celdas:
                    texto = ""
                    for p in cell.getElementsByType(P):
                        if p.firstChild:
                            texto += p.firstChild.data
                    valores.append(texto.strip())

                if i == 0:
                    encabezados = valores
                else:
                    if any(val.strip() for val in valores):  # Solo filas con contenido
                        fila_dict = dict(zip(encabezados, valores))
                        filas.append(fila_dict)

            return encabezados, filas

        except Exception as e:
            raise Exception(f"Error al leer archivo ODS: {str(e)}")

    def post(self, request, *args, **kwargs):
        archivo = request.FILES.get("file")
        if not archivo:
            return Response({"error": "No se proporcionó ningún archivo."}, status=400)

        try:
            # Detectar tipo de archivo
            tipo_archivo = self._detectar_tipo_archivo(archivo)
            print(f"📄 Tipo de archivo detectado: {tipo_archivo}")

            # Leer archivo según su tipo
            if tipo_archivo in ['xls', 'xlsx']:
                encabezados, filas_datos = self._leer_archivo_excel(archivo)
            elif tipo_archivo == 'ods':
                encabezados, filas_datos = self._leer_archivo_ods(archivo)
            else:
                return Response({
                    "error": f"Tipo de archivo no soportado. Se acepta: .xls, .xlsx, .ods"
                }, status=400)

            print(f"📋 Encabezados encontrados: {encabezados}")

            # *** USAR NUEVO SISTEMA DE MAPEO CONSOLIDADO ***
            mapeo_columnas = mapear_columnas_excel(encabezados)
            print(f"🗺️  Mapeo de columnas detectado:")
            for campo, info in mapeo_columnas.items():
                print(f"  {campo} → '{info['nombre_original']}' (score: {info['score']})")

            # Verificar que tenemos los campos esenciales
            campos_esenciales = ['cuenta']
            campos_faltantes = [c for c in campos_esenciales if c not in mapeo_columnas]

            if campos_faltantes:
                return Response({
                    "error": f"No se encontraron columnas para los campos esenciales: {campos_faltantes}",
                    "encabezados_disponibles": encabezados,
                    "mapeo_detectado": mapeo_columnas
                }, status=400)

            print(f"📊 Total de filas de datos: {len(filas_datos)}")

            # Variables de control mejoradas
            estadisticas = {
                'lineas_creadas': 0,
                'lineas_omitidas': 0,
                'errores_fecha': 0,
                'lineas_sin_valores': 0,
                'lineas_sin_subarea': 0,
                'lineas_procesadas_ok': 0
            }

            # Variables para análisis detallado
            lineas_problematicas = []
            cuentas_procesadas = []
            sumatorias_por_subarea = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})
            sumatorias_por_area = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})

            # *** PROCESAR CADA FILA CON SISTEMA CONSOLIDADO ***
            for i, fila_dict in enumerate(filas_datos, start=1):
                try:
                    # Usar función consolidada para procesar la fila
                    resultado_fila = procesar_fila_excel(fila_dict, mapeo_columnas)
                    datos = resultado_fila['datos_procesados']
                    validaciones = resultado_fila['validaciones']

                    # Verificar validaciones básicas
                    if not datos['cuenta_normalizada']:
                        if i <= 10:  # Solo log las primeras 10
                            print(f"⚠️  Fila {i}: Omitida por no tener cuenta válida")
                        estadisticas['lineas_omitidas'] += 1
                        continue

                    # Recopilar estadísticas de problemas
                    if 'fecha_invalida' in validaciones['problemas']:
                        estadisticas['errores_fecha'] += 1
                    if 'sin_valores_monetarios' in validaciones['problemas']:
                        estadisticas['lineas_sin_valores'] += 1
                    if 'sin_subarea' in validaciones['problemas']:
                        estadisticas['lineas_sin_subarea'] += 1

                    # Guardar líneas problemáticas para reporte
                    if not validaciones['es_valida']:
                        lineas_problematicas.append({
                            'fila': i,
                            'cuenta': datos['cuenta'],
                            'cuenta_normalizada': datos['cuenta_normalizada'],
                            'nombre': datos['nombre'],
                            'problemas': validaciones['problemas'],
                            'tiene_subarea': validaciones['tiene_subarea'],
                            'tiene_valores': validaciones['tiene_valores']
                        })

                    # Crear línea en base de datos
                    linea_creada = LineaFactura.objects.create(
                        subarea=datos['subarea'],
                        fecha=datos['fecha'],
                        asiento=datos['asiento'],
                        cuenta=datos['cuenta'],
                        nombre=datos['nombre'],
                        concepto=datos['concepto'],
                        debe=datos['debe'],
                        haber=datos['haber'],
                    )

                    estadisticas['lineas_creadas'] += 1
                    if validaciones['es_valida']:
                        estadisticas['lineas_procesadas_ok'] += 1

                    # Recopilar para análisis
                    cuentas_procesadas.append(datos['cuenta'])

                    # Sumar a totales por área/subárea
                    debe_val = datos['debe'] or Decimal(0)
                    haber_val = datos['haber'] or Decimal(0)

                    if datos['subarea']:
                        subarea_nombre = datos['subarea'].nombre
                        area_nombre = datos['subarea'].area.nombre

                        sumatorias_por_subarea[subarea_nombre]["debe"] += debe_val
                        sumatorias_por_subarea[subarea_nombre]["haber"] += haber_val
                        sumatorias_por_area[area_nombre]["debe"] += debe_val
                        sumatorias_por_area[area_nombre]["haber"] += haber_val
                    else:
                        sumatorias_por_area["No Clasificadas"]["debe"] += debe_val
                        sumatorias_por_area["No Clasificadas"]["haber"] += haber_val

                except Exception as e:
                    print(f"❌ ERROR al procesar fila {i}: {e}")
                    estadisticas['lineas_omitidas'] += 1
                    continue

            # *** ANÁLISIS COMPLETO DE MAPEO ***
            analisis_mapeo = analizar_mapeo_cuentas_completo(cuentas_procesadas)

            # Calcular totales finales
            total_debe = sum(v["debe"] for v in sumatorias_por_area.values())
            total_haber = sum(v["haber"] for v in sumatorias_por_area.values())

            # Generar mensaje informativo
            mensaje_base = f"{estadisticas['lineas_creadas']} líneas procesadas de {len(filas_datos)} filas del archivo {tipo_archivo.upper()}."

            # Añadir advertencias si existen problemas
            advertencias = []
            if estadisticas['lineas_sin_valores'] > 0:
                advertencias.append(f"{estadisticas['lineas_sin_valores']} sin valores monetarios")
            if estadisticas['lineas_sin_subarea'] > 0:
                advertencias.append(f"{estadisticas['lineas_sin_subarea']} sin clasificar")
            if estadisticas['errores_fecha'] > 0:
                advertencias.append(f"{estadisticas['errores_fecha']} errores de fecha")

            mensaje_final = mensaje_base
            if advertencias:
                mensaje_final += f" ADVERTENCIAS: {', '.join(advertencias)}."

            # Información de calidad del procesamiento
            porcentaje_exito = (estadisticas['lineas_procesadas_ok'] / estadisticas['lineas_creadas'] * 100) if \
            estadisticas['lineas_creadas'] > 0 else 0

            print(f"\n📊 RESUMEN FINAL:")
            print(f"Tipo de archivo: {tipo_archivo.upper()}")
            print(f"Líneas creadas: {estadisticas['lineas_creadas']}")
            print(f"Líneas procesadas OK: {estadisticas['lineas_procesadas_ok']}")
            print(f"Porcentaje de éxito: {porcentaje_exito:.1f}%")
            print(f"Cuentas mapeadas: {analisis_mapeo['estadisticas_detalladas']['mapeadas']}")
            print(f"Cuentas no mapeadas: {analisis_mapeo['estadisticas_detalladas']['no_mapeadas']}")

            return Response({
                "mensaje": mensaje_final,
                "tipo_archivo": tipo_archivo,

                # Información del mapeo de columnas
                "mapeo_columnas": {
                    "detectado": mapeo_columnas,
                    "encabezados_originales": encabezados,
                    "campos_mapeados": list(mapeo_columnas.keys()),
                    "calidad_mapeo": sum(info['score'] for info in mapeo_columnas.values()) / len(
                        mapeo_columnas) if mapeo_columnas else 0
                },

                # Estadísticas mejoradas
                "estadisticas": {
                    **estadisticas,
                    "total_filas_archivo": len(filas_datos),
                    "porcentaje_exito": round(porcentaje_exito, 2),
                    "porcentaje_mapeo": round(analisis_mapeo['estadisticas_detalladas']['porcentaje_exito'], 2)
                },

                # Análisis completo de cuentas
                "analisis_cuentas": {
                    "resumen": analisis_mapeo['estadisticas_detalladas'],
                    "cuentas_mapeadas": analisis_mapeo['cuentas_mapeadas'][:20],  # Primeras 20
                    "cuentas_no_mapeadas": analisis_mapeo['cuentas_no_mapeadas'][:20],  # Primeras 20
                    "recomendaciones": analisis_mapeo['recomendaciones']
                },

                # Sumatorias por área/subárea
                "sumatorias_por_area": {k: {"debe": float(v["debe"]), "haber": float(v["haber"])}
                                        for k, v in sumatorias_por_area.items()},
                "sumatorias_por_subarea": {k: {"debe": float(v["debe"]), "haber": float(v["haber"])}
                                           for k, v in sumatorias_por_subarea.items()},

                # Totales
                "totales": {
                    "debe": float(total_debe),
                    "haber": float(total_haber),
                    "diferencia": float(total_debe - total_haber),
                    "balanceado": abs(total_debe - total_haber) < 0.01
                },

                # Reporte de problemas (limitado para no saturar)
                "reporte_problemas": {
                    "total_lineas_con_problemas": len(lineas_problematicas),
                    "muestra_problemas": lineas_problematicas[:10],  # Solo primeros 10
                    "tipos_problemas": {
                        "fecha_invalida": len([p for p in lineas_problematicas if 'fecha_invalida' in p['problemas']]),
                        "sin_valores_monetarios": len(
                            [p for p in lineas_problematicas if 'sin_valores_monetarios' in p['problemas']]),
                        "sin_subarea": len([p for p in lineas_problematicas if 'sin_subarea' in p['problemas']]),
                        "cuenta_vacia": len([p for p in lineas_problematicas if 'cuenta_vacia' in p['problemas']])
                    }
                }

            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback
            print(f"Error completo: {traceback.format_exc()}")
            return Response({"error": str(e)}, status=500)


class ResumenMensualView(APIView):
    def get(self, request, *args, **kwargs):
        anio = request.query_params.get("año")
        mes = request.query_params.get("mes")

        if not anio or not mes:
            return Response({"error": "Debe proporcionar 'año' y 'mes' como parámetros."}, status=400)

        try:
            anio = int(anio)
            mes = int(mes)
        except ValueError:
            return Response({"error": "'año' y 'mes' deben ser números."}, status=400)

        # Filtrar por año y mes, permitiendo fechas NULL
        lineas = LineaFactura.objects.filter(
            fecha__year=anio,
            fecha__month=mes
        ) if anio and mes else LineaFactura.objects.filter(
            fecha__isnull=True  # Para líneas sin fecha válida
        )

        sumatorias_por_area = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})
        sumatorias_por_subarea = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})

        for linea in lineas:
            debe = linea.debe or Decimal(0)
            haber = linea.haber or Decimal(0)

            if linea.subarea:
                sumatorias_por_subarea[linea.subarea.nombre]["debe"] += debe
                sumatorias_por_subarea[linea.subarea.nombre]["haber"] += haber
                area_nombre = linea.subarea.area.nombre
                sumatorias_por_area[area_nombre]["debe"] += debe
                sumatorias_por_area[area_nombre]["haber"] += haber

        total_debe = sum(v["debe"] for v in sumatorias_por_area.values())
        total_haber = sum(v["haber"] for v in sumatorias_por_area.values())

        return Response({
            "año": anio,
            "mes": mes,
            "sumatorias_por_area": sumatorias_por_area,
            "sumatorias_por_subarea": sumatorias_por_subarea,
            "total_debe": float(total_debe),
            "total_haber": float(total_haber),
            "balanceado": total_debe == total_haber
        }, status=status.HTTP_200_OK)


# Nuevo endpoint para análisis de duplicados existentes en BD
class AnalisisDuplicadosView(APIView):
    """
    Endpoint adicional para analizar duplicados ya existentes en la base de datos
    """

    def get(self, request, *args, **kwargs):
        from django.db.models import Count

        # Buscar duplicados en la base de datos
        duplicados_bd = LineaFactura.objects.values(
            'fecha', 'asiento', 'cuenta', 'nombre', 'concepto', 'debe', 'haber'
        ).annotate(
            count=Count('id')
        ).filter(count__gt=1).order_by('-count')

        duplicados_detalle = []
        total_debe_duplicados_bd = Decimal(0)
        total_haber_duplicados_bd = Decimal(0)

        for dup in duplicados_bd:
            # Obtener todas las instancias de este duplicado
            instancias = LineaFactura.objects.filter(
                fecha=dup['fecha'],
                asiento=dup['asiento'],
                cuenta=dup['cuenta'],
                nombre=dup['nombre'],
                concepto=dup['concepto'],
                debe=dup['debe'],
                haber=dup['haber']
            )

            # Sumar valores de duplicados (excluyendo la primera instancia)
            for instancia in instancias[1:]:  # Saltar la primera
                total_debe_duplicados_bd += instancia.debe or Decimal(0)
                total_haber_duplicados_bd += instancia.haber or Decimal(0)

            duplicados_detalle.append({
                "fecha": dup['fecha'],
                "asiento": dup['asiento'],
                "cuenta": dup['cuenta'],
                "nombre": dup['nombre'],
                "concepto": dup['concepto'],
                "debe": float(dup['debe']) if dup['debe'] else 0.0,
                "haber": float(dup['haber']) if dup['haber'] else 0.0,
                "cantidad_duplicados": dup['count'],
                "ids": [inst.id for inst in instancias]
            })

        return Response({
            "duplicados_en_bd": {
                "cantidad_grupos": len(duplicados_bd),
                "total_debe_duplicados": float(total_debe_duplicados_bd),
                "total_haber_duplicados": float(total_haber_duplicados_bd),
                "detalles": duplicados_detalle
            }
        })


class LineasFacturaListView(APIView):
    def get(self, request, *args, **kwargs):
        anio = request.query_params.get("año")
        mes = request.query_params.get("mes")

        if not anio or not mes:
            return Response({"error": "Debe proporcionar 'año' y 'mes' como parámetros."}, status=400)

        try:
            anio = int(anio)
            mes = int(mes)
        except ValueError:
            return Response({"error": "'año' y 'mes' deben ser números."}, status=400)

        lineas = LineaFactura.objects.filter(
            fecha__year=anio,
            fecha__month=mes
        ).order_by("fecha", "asiento")

        serializer = LineaFacturaSerializer(lineas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LineaFacturaPagination(PageNumberPagination):
    page_size = 100


class LineasFacturaSampleListView(ListAPIView):
    queryset = LineaFactura.objects.all().order_by("fecha", "asiento")
    serializer_class = LineaFacturaSimpleSerializer
    pagination_class = LineaFacturaPagination