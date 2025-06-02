from ..models import LineaFactura
from ..serializers.serializers import LineaFacturaSerializer
from ..utils.utils import buscar_subarea_por_cuenta
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status


class FacturaUploadView(APIView):
    parser_classes = [MultiPartParser]

    def _parse_fecha(self, fecha_valor):
        """
        Parsea fechas en múltiples formatos de manera más robusta
        """
        if not fecha_valor or (isinstance(fecha_valor, str) and fecha_valor.strip() == ""):
            return None

        try:
            # Si pandas ya lo convirtió a datetime
            if hasattr(fecha_valor, 'date'):
                return fecha_valor.date()

            # Si es un objeto datetime de pandas (Timestamp)
            if str(type(fecha_valor)) == "<class 'pandas._libs.tslibs.timestamps.Timestamp'>":
                return fecha_valor.date()

            # Si es número (serial de Excel/ODS)
            if isinstance(fecha_valor, (int, float)):
                # Verificar que sea un número razonable para una fecha
                if 1 <= fecha_valor <= 100000:  # Rango razonable para fechas Excel
                    excel_epoch = datetime(1900, 1, 1)
                    days = int(fecha_valor) - 2  # -2 por el bug histórico de Excel
                    fecha_calculada = excel_epoch + timedelta(days=days)
                    return fecha_calculada.date()

            # Convertir a string y limpiar
            fecha_str = str(fecha_valor).strip()

            # Manejar valores vacíos o nulos
            if fecha_str.lower() in ['nan', 'nat', 'none', '', 'null']:
                return None

            # Lista de formatos a probar en orden
            formatos_fecha = [
                # Formatos con tiempo (más específicos primero)
                "%Y-%m-%d %H:%M:%S",  # 2024-12-31 00:00:00
                "%d/%m/%Y %H:%M:%S",  # 31/12/2024 00:00:00
                "%Y-%m-%dT%H:%M:%S",  # 2024-12-31T00:00:00

                # Formatos solo fecha
                "%d/%m/%Y",  # 31/12/2024 (formato español)
                "%Y-%m-%d",  # 2024-12-31 (formato ISO)
                "%m/%d/%Y",  # 12/31/2024 (formato americano)
                "%d-%m-%Y",  # 31-12-2024
                "%Y/%m/%d",  # 2024/12/31

                # Formatos con año corto
                "%d/%m/%y",  # 31/12/24
                "%d-%m-%y",  # 31-12-24
                "%y/%m/%d",  # 24/12/31

                # Otros formatos
                "%d.%m.%Y",  # 31.12.2024
                "%d %m %Y",  # 31 12 2024
                "%Y%m%d",  # 20241231
                "%d-%b-%Y",  # 31-Dec-2024
                "%d %b %Y",  # 31 Dec 2024
            ]

            # Intentar cada formato
            for formato in formatos_fecha:
                try:
                    fecha_parseada = datetime.strptime(fecha_str, formato)
                    return fecha_parseada.date()
                except ValueError:
                    # ⚠️ Si el formato tiene tiempo, intenta truncar a solo fecha
                    if " " in fecha_str:
                        try:
                            fecha_solo_fecha = fecha_str.split(" ")[0]
                            fecha_parseada = datetime.strptime(fecha_solo_fecha, "%Y-%m-%d")
                            return fecha_parseada.date()
                        except:
                            pass

            # Si es string numérico, intentar como serial de Excel
            try:
                numero_serial = float(fecha_str)
                if 1 <= numero_serial <= 100000:  # Rango razonable
                    excel_epoch = datetime(1900, 1, 1)
                    days = int(numero_serial) - 2
                    fecha_calculada = excel_epoch + timedelta(days=days)
                    return fecha_calculada.date()
            except ValueError:
                pass

            # Último intento: usar dateutil.parser si está disponible
            try:
                from dateutil import parser
                fecha_parseada = parser.parse(fecha_str, dayfirst=True)  # Día primero (formato español)
                return fecha_parseada.date()
            except Exception as e:
                print(f"📛 dateutil no pudo parsear: {fecha_str} → {e}")

        except Exception as e:
            print(f"❌ Error inesperado al parsear fecha '{fecha_valor}': {e}")

        print(f"⚠️  No se pudo parsear la fecha '{fecha_valor}' (tipo: {type(fecha_valor)})")
        return None

    def _parse_decimal(self, valor):
        """
        Convierte valores a Decimal manejando diferentes formatos
        """
        try:
            if not valor:
                return None
            if isinstance(valor, (int, float)):
                return Decimal(str(valor))
            return Decimal(str(valor).replace(",", "")) if valor else None
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _detectar_tipo_archivo(self, archivo):
        """
        Detecta el tipo de archivo basado en la extensión
        """
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
        """
        encabezados_esperados = ['Fecha', 'Asto', 'Doc', 'Cuenta', 'Nombre', 'Concepto', 'Debe', 'Haber']

        # Buscar en las primeras 10 filas
        for fila_idx in range(min(10, len(df))):
            fila_valores = [str(val).strip() for val in df.iloc[fila_idx].values if pd.notna(val)]

            # Contar cuántos encabezados esperados encontramos
            coincidencias = sum(1 for encabezado in encabezados_esperados
                                if any(encabezado.lower() in str(val).lower() for val in fila_valores))

            # Si encontramos al menos 4 encabezados esperados, probablemente es la fila correcta
            if coincidencias >= 4:
                print(f"🎯 Encabezados detectados en fila {fila_idx + 1}: {fila_valores}")
                return fila_idx

        # Si no encontramos encabezados, asumir que están en la fila 0
        print("⚠️  No se detectaron encabezados automáticamente, usando fila 1")
        return 0

    def _leer_archivo_excel(self, archivo):
        """
        Lee archivos Excel (.xls y .xlsx) usando pandas
        """
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
                date_parser=None,  # No parsear fechas automáticamente
                keep_default_na=False,  # Mantener valores como están
            )

            # Limpiar nombres de columnas
            df.columns = [str(col).strip() if pd.notna(col) else f"Columna_{i}"
                          for i, col in enumerate(df.columns)]

            # Eliminar filas completamente vacías
            df = df.dropna(how='all')

            # Convertir DataFrame a formato similar al original
            encabezados = df.columns.tolist()
            filas = []

            for index, row in df.iterrows():
                valores = [str(val).strip() if pd.notna(val) else "" for val in row.values]
                # Solo incluir filas que tengan al menos una celda con contenido
                if any(val.strip() for val in valores):
                    filas.append(valores)

            return encabezados, filas

        except Exception as e:
            raise Exception(f"Error al leer archivo Excel: {str(e)}")

    def _leer_archivo_ods(self, archivo):
        """
        Lee archivos ODS usando la librería original
        """
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
                    filas.append(valores)

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
            print(f"📊 Total de filas de datos: {len(filas_datos)}")

            # Variables de control
            lineas_creadas = 0
            lineas_omitidas = 0
            lineas_no_clasificadas = 0
            errores_fecha = 0

            # NUEVAS VARIABLES PARA VALIDACIÓN COMPLETA
            cuentas_no_clasificadas = set()
            lineas_sin_debe_haber = []
            lineas_formato_incorrecto = []
            lineas_problematicas = []

            # Variables para verificación
            lineas_procesadas_detalle = []
            total_filas_archivo = len(filas_datos)

            sumatorias_por_subarea = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})
            sumatorias_por_area = defaultdict(lambda: {"debe": Decimal(0), "haber": Decimal(0)})

            # Procesar cada fila
            for i, valores in enumerate(filas_datos, start=1):
                fila_dict = dict(zip(encabezados, valores))

                # Verificar que tenga cuenta (requisito mínimo)
                # Buscar el campo "Cuenta" de manera flexible
                cuenta = ""
                for campo in ["Cuenta", "cuenta", "CUENTA", "Cta"]:
                    if campo in fila_dict:
                        cuenta = str(fila_dict[campo]).strip()
                        break

                # Si no tiene cuenta o es una fila de encabezado/título, omitir
                if not cuenta or cuenta in ["Cuenta", "cuenta", "CUENTA", ""]:
                    if i <= 10:  # Solo mostrar las primeras 10 omisiones para no saturar el log
                        print(f"⚠️  Fila {i + 1}: Omitida por no tener cuenta válida (valor: '{cuenta}')")
                    continue

                # Parsear fecha - buscar campo fecha de manera flexible
                fecha_valor = ""
                for campo in ["Fecha", "fecha", "FECHA", "Date"]:
                    if campo in fila_dict:
                        fecha_valor = fila_dict[campo]
                        break

                fecha_formateada = self._parse_fecha(fecha_valor)

                # Debug mejorado para fechas - mostrar más ejemplos
                if fecha_valor and not fecha_formateada:
                    errores_fecha += 1
                    if errores_fecha <= 10:  # Mostrar los primeros 10 errores
                        print(
                            f"❌ FECHA ERROR #{errores_fecha} - Fila {i + 1}: '{fecha_valor}' (tipo: {type(fecha_valor)})")
                elif fecha_valor and fecha_formateada:
                    if i <= 10:  # Mostrar los primeros 10 éxitos para verificar
                        print(f"✅ FECHA OK - Fila {i + 1}: '{fecha_valor}' → {fecha_formateada}")
                elif not fecha_valor:
                    if i <= 3:  # Solo mostrar las primeras para no saturar
                        print(f"⚪ FECHA VACÍA - Fila {i + 1}: Campo fecha está vacío")

                # Parsear valores monetarios - buscar campos de manera flexible
                debe_original = ""
                haber_original = ""
                concepto = ""

                for campo in ["Debe", "debe", "DEBE", "Debit"]:
                    if campo in fila_dict:
                        debe_original = str(fila_dict[campo]).strip()
                        break

                for campo in ["Haber", "haber", "HABER", "Credit"]:
                    if campo in fila_dict:
                        haber_original = str(fila_dict[campo]).strip()
                        break

                for campo in ["Concepto", "concepto", "CONCEPTO", "Descripcion", "Description"]:
                    if campo in fila_dict:
                        concepto = str(fila_dict[campo]).strip()
                        break

                debe = self._parse_decimal(debe_original)
                haber = self._parse_decimal(haber_original)

                # *** VALIDACIONES COMPLETAS ***
                problemas_fila = []

                # 1. VALIDAR QUE TENGA VALORES DEBE O HABER
                if not debe and not haber:
                    # Verificar si hay valor en concepto (formato incorrecto)
                    valor_en_concepto = self._parse_decimal(concepto)
                    if valor_en_concepto:
                        problema = {
                            "tipo": "formato_incorrecto",
                            "descripcion": f"Valor {valor_en_concepto} encontrado en 'Concepto' en lugar de 'Debe/Haber'",
                            "valor_detectado": float(valor_en_concepto),
                            "campo_origen": "Concepto",
                            "solucion": "Mover el valor al campo 'Debe' o 'Haber' correspondiente"
                        }
                        problemas_fila.append(problema)
                        lineas_formato_incorrecto.append({
                            "fila": i + 1,
                            "cuenta": cuenta,
                            "nombre": fila_dict.get("Nombre", ""),
                            "concepto_original": concepto,
                            "valor_detectado": float(valor_en_concepto),
                            "problema": "Valor monetario en campo 'Concepto'"
                        })
                        print(
                            f"🔴 FORMATO INCORRECTO - Fila {i + 1}: Valor {valor_en_concepto} en 'Concepto' (Cuenta: {cuenta})")
                    else:
                        problema = {
                            "tipo": "sin_valores_monetarios",
                            "descripcion": "Línea sin valores en 'Debe' ni 'Haber'",
                            "debe_original": debe_original,
                            "haber_original": haber_original,
                            "solucion": "Verificar si esta línea debe tener valores monetarios"
                        }
                        problemas_fila.append(problema)
                        lineas_sin_debe_haber.append({
                            "fila": i + 1,
                            "cuenta": cuenta,
                            "nombre": fila_dict.get("Nombre", ""),
                            "concepto": concepto,
                            "debe_original": debe_original,
                            "haber_original": haber_original,
                            "problema": "Sin valores monetarios en Debe ni Haber"
                        })
                        print(f"🔴 SIN VALORES - Fila {i + 1}: No tiene valores en Debe ni Haber (Cuenta: {cuenta})")

                # 2. VALIDAR CLASIFICACIÓN POR ÁREA/SUBÁREA
                subarea = buscar_subarea_por_cuenta(cuenta)  # Esta función debe estar definida en tu código
                if not subarea:
                    lineas_no_clasificadas += 1
                    cuentas_no_clasificadas.add(cuenta)
                    problema = {
                        "tipo": "cuenta_no_clasificada",
                        "descripcion": f"La cuenta '{cuenta}' no está asignada a ningún área/subárea",
                        "solucion": "Añadir esta cuenta al sistema de clasificación de áreas"
                    }
                    problemas_fila.append(problema)
                    print(
                        f"🔴 NO CLASIFICADA - Fila {i + 1}: Cuenta '{cuenta}' ({fila_dict.get('Nombre', 'Sin nombre')})")

                # Guardar líneas problemáticas para reporte
                if problemas_fila:
                    lineas_problematicas.append({
                        "fila": i + 1,
                        "cuenta": cuenta,
                        "nombre": fila_dict.get("Nombre", ""),
                        "concepto": concepto,
                        "debe": debe_original,
                        "haber": haber_original,
                        "problemas": problemas_fila
                    })

                # *** CREAR LÍNEAS EN BASE DE DATOS ***
                try:
                    # Buscar otros campos de manera flexible
                    asiento = ""
                    nombre = ""

                    for campo in ["Asto", "asto", "ASTO", "Asiento", "asiento"]:
                        if campo in fila_dict:
                            asiento = str(fila_dict[campo]).strip()
                            break

                    for campo in ["Nombre", "nombre", "NOMBRE", "Name", "Descripcion"]:
                        if campo in fila_dict:
                            nombre = str(fila_dict[campo]).strip()
                            break

                    linea_creada = LineaFactura.objects.create(  # Asegúrate de importar este modelo
                        subarea=subarea,
                        fecha=fecha_formateada,
                        asiento=asiento,
                        cuenta=cuenta,
                        nombre=nombre,
                        concepto=concepto,
                        debe=debe,
                        haber=haber,
                    )
                    lineas_creadas += 1

                    # Guardar detalle para verificación
                    detalle_linea = {
                        "fila_archivo": i + 1,
                        "id_bd": linea_creada.id,
                        "cuenta": cuenta,
                        "debe": float(debe) if debe else 0.0,
                        "haber": float(haber) if haber else 0.0,
                        "tiene_subarea": subarea is not None,
                        "tiene_problemas": len(problemas_fila) > 0
                    }
                    lineas_procesadas_detalle.append(detalle_linea)

                    # Sumar a totales
                    if subarea:
                        sumatorias_por_subarea[subarea.nombre]["debe"] += debe or Decimal(0)
                        sumatorias_por_subarea[subarea.nombre]["haber"] += haber or Decimal(0)
                        area_nombre = subarea.area.nombre
                        sumatorias_por_area[area_nombre]["debe"] += debe or Decimal(0)
                        sumatorias_por_area[area_nombre]["haber"] += haber or Decimal(0)
                    else:
                        sumatorias_por_area["No Clasificadas"]["debe"] += debe or Decimal(0)
                        sumatorias_por_area["No Clasificadas"]["haber"] += haber or Decimal(0)

                except Exception as e:
                    print(f"❌ ERROR al crear línea {i + 1} (cuenta {cuenta}): {e}")
                    lineas_omitidas += 1
                    continue

            # Calcular totales finales
            total_debe = sum(v["debe"] for v in sumatorias_por_area.values())
            total_haber = sum(v["haber"] for v in sumatorias_por_area.values())

            # Calcular totales de TODAS las líneas procesadas
            total_debe_todas_lineas = sum(detalle["debe"] for detalle in lineas_procesadas_detalle)
            total_haber_todas_lineas = sum(detalle["haber"] for detalle in lineas_procesadas_detalle)

            # Mensaje informativo
            mensaje = f"{lineas_creadas} líneas procesadas de {total_filas_archivo} filas del archivo {tipo_archivo.upper()}."

            # Añadir advertencias al mensaje
            advertencias = []
            if len(lineas_sin_debe_haber) > 0:
                advertencias.append(f"{len(lineas_sin_debe_haber)} líneas sin valores monetarios")
            if len(lineas_formato_incorrecto) > 0:
                advertencias.append(f"{len(lineas_formato_incorrecto)} líneas con formato incorrecto")
            if lineas_no_clasificadas > 0:
                advertencias.append(f"{lineas_no_clasificadas} líneas sin clasificar")
            if errores_fecha > 0:
                advertencias.append(f"{errores_fecha} errores de fecha")

            if advertencias:
                mensaje += f" ADVERTENCIAS: {', '.join(advertencias)}."

            # Verificación final
            diferencia_debe = 5823021.30 - total_debe_todas_lineas
            diferencia_haber = 5823021.30 - total_haber_todas_lineas

            print(f"\n📊 RESUMEN FINAL:")
            print(f"Tipo de archivo: {tipo_archivo.upper()}")
            print(f"Total líneas procesadas: {len(lineas_procesadas_detalle)}")
            print(f"Líneas con problemas: {len(lineas_problematicas)}")
            print(f"Diferencia en Debe: {diferencia_debe:.2f}")
            print(f"Diferencia en Haber: {diferencia_haber:.2f}")

            return Response({
                "mensaje": mensaje,
                "tipo_archivo": tipo_archivo,

                # Estadísticas básicas
                "estadisticas": {
                    "total_filas_archivo": total_filas_archivo,
                    "lineas_creadas": lineas_creadas,
                    "lineas_omitidas": lineas_omitidas,
                    "lineas_no_clasificadas": lineas_no_clasificadas,
                    "errores_fecha": errores_fecha
                },

                # Sumatorias por área/subárea
                "sumatorias_por_area": sumatorias_por_area,
                "sumatorias_por_subarea": sumatorias_por_subarea,

                # Totales
                "totales_clasificados": {
                    "debe": float(total_debe),
                    "haber": float(total_haber),
                    "balanceado": total_debe == total_haber
                },
                "totales_todas_lineas": {
                    "debe": total_debe_todas_lineas,
                    "haber": total_haber_todas_lineas,
                    "balanceado": abs(total_debe_todas_lineas - total_haber_todas_lineas) < 0.01
                },

                # Verificación contra archivo original
                "verificacion_archivo": {
                    "debe_esperado": 5823021.30,
                    "haber_esperado": 5823021.30,
                    "diferencia_debe": diferencia_debe,
                    "diferencia_haber": diferencia_haber,
                    "coincide_perfectamente": (
                            abs(diferencia_debe) < 0.01 and abs(diferencia_haber) < 0.01
                    )
                },

                # Reporte completo de problemas
                "reporte_problemas": {
                    "resumen": {
                        "total_lineas_con_problemas": len(lineas_problematicas),
                        "lineas_sin_valores_monetarios": len(lineas_sin_debe_haber),
                        "lineas_formato_incorrecto": len(lineas_formato_incorrecto),
                        "cuentas_no_clasificadas": len(cuentas_no_clasificadas)
                    },

                    "lineas_sin_debe_haber": {
                        "cantidad": len(lineas_sin_debe_haber),
                        "descripcion": "Líneas que no tienen valores en campos 'Debe' ni 'Haber'",
                        "accion_requerida": "Verificar si estas líneas deben tener valores monetarios o eliminarlas",
                        "detalles": lineas_sin_debe_haber
                    },

                    "lineas_formato_incorrecto": {
                        "cantidad": len(lineas_formato_incorrecto),
                        "descripcion": "Líneas con valores monetarios en campos incorrectos",
                        "accion_requerida": "Mover los valores al campo 'Debe' o 'Haber' correspondiente",
                        "detalles": lineas_formato_incorrecto
                    },

                    "cuentas_no_clasificadas": {
                        "cantidad": len(cuentas_no_clasificadas),
                        "descripcion": "Cuentas que no están asignadas a ningún área/subárea",
                        "accion_requerida": "Añadir estas cuentas al sistema de clasificación",
                        "cuentas": sorted(list(cuentas_no_clasificadas))
                    },

                    "detalle_completo": lineas_problematicas
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


class LineasFacturaSampleListView(APIView):
    def get(self, request, *args, **kwargs):
        lineas = LineaFactura.objects.all().order_by("fecha", "asiento")

        serializer = LineaFacturaSerializer(lineas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
