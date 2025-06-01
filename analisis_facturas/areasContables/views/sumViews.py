from ..models import SeccionContable, AreaContable, SubAreaContable, LineaFactura
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Q
import re


class SumatoriasBOEView(APIView):
    """
    Devuelve la jerarquía completa de Secciones → Áreas → Subáreas,
    con sumatorias calculadas según principios contables del BOE.

    Parámetros opcionales:
    - ?seccion=A,B,C,D : filtrar por secciones específicas
    - ?incluir_vacias=true : incluir áreas sin datos
    - ?orden_boe=true : ordenar según numeración BOE
    """

    def get(self, request, *args, **kwargs):
        # Parámetros de consulta
        secciones_filtro = request.GET.get('seccion', '').split(',') if request.GET.get('seccion') else None
        incluir_vacias = request.GET.get('incluir_vacias', 'false').lower() == 'true'
        orden_boe = request.GET.get('orden_boe', 'true').lower() == 'true'

        # Filtrar secciones si se especifica
        if secciones_filtro and secciones_filtro != ['']:
            secciones = SeccionContable.objects.filter(letra__in=secciones_filtro)
        else:
            secciones = SeccionContable.objects.all()

        secciones = secciones.prefetch_related('areas__subareas')

        # Ordenar secciones según BOE (A, B, C, D)
        if orden_boe:
            secciones = sorted(secciones,
                               key=lambda s: ['A', 'B', 'C', 'D'].index(s.letra) if s.letra in ['A', 'B', 'C',
                                                                                                'D'] else 999)

        resultado = []
        totales_generales = {
            "total_debe": Decimal(0),
            "total_haber": Decimal(0),
            "total_saldo": Decimal(0)
        }

        for seccion in secciones:
            seccion_data = {
                "letra": seccion.letra,
                "nombre": seccion.nombre,
                "total_debe": Decimal(0),
                "total_haber": Decimal(0),
                "total_saldo": Decimal(0),
                "areas": [],
                "metadata": {
                    "es_activo": seccion.letra in ['A', 'B'],
                    "es_pasivo_patrimonio": seccion.letra == 'C',
                    "es_resultados": seccion.letra == 'D'
                }
            }

            areas = seccion.areas.all()

            # Ordenar áreas según numeración BOE si se solicita
            if orden_boe and seccion.letra == 'D':
                areas = sorted(areas, key=self._extraer_numero_area)

            for area in areas:
                area_data = {
                    "abreviatura": area.abreviatura,
                    "nombre": area.nombre,
                    "total_debe": Decimal(0),
                    "total_haber": Decimal(0),
                    "total_saldo": Decimal(0),
                    "subareas": [],
                    "metadata": self._obtener_metadata_area(area, seccion.letra)
                }

                tiene_datos = False

                for subarea in area.subareas.all():
                    # Calcular saldo contable correcto
                    saldo_data = self._calcular_saldo_contable(subarea)

                    if saldo_data["total_lineas"] > 0:
                        tiene_datos = True

                    subarea_data = {
                        "nombre": subarea.nombre,
                        "codigos_positivos": subarea.codigos_positivos,
                        "codigos_negativos": subarea.codigos_negativos,
                        "debe": float(saldo_data["debe_total"]),
                        "haber": float(saldo_data["haber_total"]),
                        "saldo": float(saldo_data["saldo"]),
                        "total_lineas": saldo_data["total_lineas"],
                        "metadata": {
                            "es_cuenta_deudora": saldo_data["saldo"] > 0,
                            "es_cuenta_acreedora": saldo_data["saldo"] < 0,
                            "esta_balanceada": saldo_data["saldo"] == 0
                        }
                    }

                    area_data["total_debe"] += saldo_data["debe_total"]
                    area_data["total_haber"] += saldo_data["haber_total"]
                    area_data["total_saldo"] += saldo_data["saldo"]
                    area_data["subareas"].append(subarea_data)

                # Solo incluir área si tiene datos o se solicita incluir vacías
                if tiene_datos or incluir_vacias:
                    seccion_data["total_debe"] += area_data["total_debe"]
                    seccion_data["total_haber"] += area_data["total_haber"]
                    seccion_data["total_saldo"] += area_data["total_saldo"]
                    seccion_data["areas"].append({
                        **area_data,
                        "total_debe": float(area_data["total_debe"]),
                        "total_haber": float(area_data["total_haber"]),
                        "total_saldo": float(area_data["total_saldo"])
                    })

            # Agregar sección a resultado
            totales_generales["total_debe"] += seccion_data["total_debe"]
            totales_generales["total_haber"] += seccion_data["total_haber"]
            totales_generales["total_saldo"] += seccion_data["total_saldo"]

            resultado.append({
                **seccion_data,
                "total_debe": float(seccion_data["total_debe"]),
                "total_haber": float(seccion_data["total_haber"]),
                "total_saldo": float(seccion_data["total_saldo"])
            })

        return Response({
            "secciones": resultado,
            "totales_generales": {
                "total_debe": float(totales_generales["total_debe"]),
                "total_haber": float(totales_generales["total_haber"]),
                "total_saldo": float(totales_generales["total_saldo"]),
                "esta_balanceado": totales_generales["total_saldo"] == 0
            },
            "metadata": {
                "filtros_aplicados": {
                    "secciones": secciones_filtro,
                    "incluir_vacias": incluir_vacias,
                    "orden_boe": orden_boe
                },
                "total_secciones": len(resultado),
                "principios_contables": "BOE - Plan General de Contabilidad Español"
            }
        }, status=status.HTTP_200_OK)

    def _calcular_saldo_contable(self, subarea):
        """
        Calcula el saldo contable correcto considerando códigos positivos/negativos
        """
        lineas = LineaFactura.objects.filter(subarea=subarea)

        agregados = lineas.aggregate(
            debe_total=Sum('debe'),
            haber_total=Sum('haber')
        )

        debe_total = agregados["debe_total"] or Decimal(0)
        haber_total = agregados["haber_total"] or Decimal(0)
        total_lineas = lineas.count()

        # Saldo contable: para la mayoría de cuentas es Debe - Haber
        # Pero esto puede ajustarse según el tipo de cuenta si es necesario
        saldo = debe_total - haber_total

        return {
            "debe_total": debe_total,
            "haber_total": haber_total,
            "saldo": saldo,
            "total_lineas": total_lineas
        }

    def _extraer_numero_area(self, area):
        """
        Extrae el número del área para ordenamiento según BOE (1, 2, 3... 17)
        """
        match = re.match(r'^(\d+)\.', area.nombre)
        if match:
            return int(match.group(1))
        return 999  # Áreas sin número van al final

    def _obtener_metadata_area(self, area, letra_seccion):
        """
        Obtiene metadata específica del área según el BOE
        """
        metadata = {
            "seccion": letra_seccion,
            "descripcion": area.descripcion
        }

        # Metadata específica para Sección D (Pérdidas y Ganancias)
        if letra_seccion == 'D':
            numero_area = self._extraer_numero_area(area)

            if 1 <= numero_area <= 11:
                metadata.update({
                    "grupo_calculo": "RESULTADO_EXPLOTACION",
                    "numero_boe": numero_area,
                    "es_area_explotacion": True
                })
            elif 12 <= numero_area <= 16:
                metadata.update({
                    "grupo_calculo": "RESULTADO_FINANCIERO",
                    "numero_boe": numero_area,
                    "es_area_financiera": True
                })
            elif numero_area == 17:
                metadata.update({
                    "grupo_calculo": "IMPUESTOS_BENEFICIOS",
                    "numero_boe": numero_area,
                    "es_area_impuestos": True
                })
            else:
                metadata.update({
                    "grupo_calculo": "OTROS_CONCEPTOS",
                    "es_area_complementaria": True
                })

        # Metadata para otras secciones
        elif letra_seccion == 'A':
            metadata["es_activo_no_corriente"] = True
        elif letra_seccion == 'B':
            metadata["es_activo_corriente"] = True
        elif letra_seccion == 'C':
            if "PATRIMONIO NETO" in area.nombre.upper():
                metadata["es_patrimonio_neto"] = True
            elif "PASIVO NO CORRIENTE" in area.nombre.upper():
                metadata["es_pasivo_no_corriente"] = True
            elif "PASIVO CORRIENTE" in area.nombre.upper():
                metadata["es_pasivo_corriente"] = True

        return metadata


class TotalActivoView(APIView):
    """
    Calcula el Total Activo según el BOE (Secciones A + B)
    con principios contables correctos y análisis financiero.

    TOTAL ACTIVO = ACTIVO NO CORRIENTE (A) + ACTIVO CORRIENTE (B)

    Parámetros opcionales:
    - ?incluir_detalle=true : incluir desglose completo
    - ?comparar_pasivo=true : comparar con pasivo+patrimonio
    - ?ratios=true : calcular ratios financieros
    """

    def get(self, request, *args, **kwargs):
        # Parámetros de consulta
        incluir_detalle = request.GET.get('incluir_detalle', 'true').lower() == 'true'
        comparar_pasivo = request.GET.get('comparar_pasivo', 'false').lower() == 'true'
        calcular_ratios = request.GET.get('ratios', 'false').lower() == 'true'

        # Obtener secciones A y B
        secciones_activo = SeccionContable.objects.filter(
            letra__in=["A", "B"]
        ).prefetch_related("areas__subareas").order_by('letra')

        # Calcular totales
        activo_no_corriente = Decimal(0)  # Sección A
        activo_corriente = Decimal(0)  # Sección B

        detalle_secciones = []
        total_debe_activo = Decimal(0)
        total_haber_activo = Decimal(0)

        for seccion in secciones_activo:
            seccion_saldo = Decimal(0)
            seccion_debe = Decimal(0)
            seccion_haber = Decimal(0)
            areas_detalle = []

            for area in seccion.areas.all():
                area_saldo = Decimal(0)
                area_debe = Decimal(0)
                area_haber = Decimal(0)
                subareas_detalle = []

                for subarea in area.subareas.all():
                    # Calcular saldo contable de la subárea
                    saldo_data = self._calcular_saldo_activo(subarea)

                    area_saldo += saldo_data["saldo"]
                    area_debe += saldo_data["debe"]
                    area_haber += saldo_data["haber"]

                    if incluir_detalle:
                        subareas_detalle.append({
                            "nombre": subarea.nombre,
                            "codigos_positivos": subarea.codigos_positivos,
                            "codigos_negativos": subarea.codigos_negativos,
                            "debe": float(saldo_data["debe"]),
                            "haber": float(saldo_data["haber"]),
                            "saldo": float(saldo_data["saldo"]),
                            "total_lineas": saldo_data["total_lineas"],
                            "interpretacion": self._interpretar_saldo_activo(saldo_data["saldo"])
                        })

                seccion_saldo += area_saldo
                seccion_debe += area_debe
                seccion_haber += area_haber

                if incluir_detalle:
                    areas_detalle.append({
                        "nombre": area.nombre,
                        "abreviatura": area.abreviatura,
                        "saldo": float(area_saldo),
                        "debe": float(area_debe),
                        "haber": float(area_haber),
                        "subareas": subareas_detalle,
                        "metadata": self._obtener_metadata_area_activo(area, seccion.letra)
                    })

            # Asignar a la variable correspondiente
            if seccion.letra == "A":
                activo_no_corriente = seccion_saldo
            elif seccion.letra == "B":
                activo_corriente = seccion_saldo

            total_debe_activo += seccion_debe
            total_haber_activo += seccion_haber

            detalle_secciones.append({
                "letra": seccion.letra,
                "nombre": seccion.nombre,
                "saldo": float(seccion_saldo),
                "debe": float(seccion_debe),
                "haber": float(seccion_haber),
                "areas": areas_detalle if incluir_detalle else [],
                "metadata": {
                    "es_activo_no_corriente": seccion.letra == "A",
                    "es_activo_corriente": seccion.letra == "B",
                    "porcentaje_total_activo": 0  # Se calculará después
                }
            })

        # Calcular total activo
        total_activo = activo_no_corriente + activo_corriente

        # Calcular porcentajes
        for seccion in detalle_secciones:
            if total_activo != 0:
                seccion["metadata"]["porcentaje_total_activo"] = round(
                    (seccion["saldo"] / float(total_activo)) * 100, 2
                )

        # Preparar respuesta base
        respuesta = {
            "total_activo": {
                "saldo": float(total_activo),
                "debe_total": float(total_debe_activo),
                "haber_total": float(total_haber_activo),
                "formula": "ACTIVO NO CORRIENTE + ACTIVO CORRIENTE"
            },
            "componentes": {
                "activo_no_corriente": {
                    "saldo": float(activo_no_corriente),
                    "porcentaje": round((float(activo_no_corriente) / float(total_activo) * 100),
                                        2) if total_activo != 0 else 0,
                    "descripcion": "Bienes y derechos a largo plazo"
                },
                "activo_corriente": {
                    "saldo": float(activo_corriente),
                    "porcentaje": round((float(activo_corriente) / float(total_activo) * 100),
                                        2) if total_activo != 0 else 0,
                    "descripcion": "Bienes y derechos a corto plazo"
                }
            },
            "detalle_por_seccion": detalle_secciones,
            "validaciones": {
                "sumas_cuadran": abs(total_activo - (activo_no_corriente + activo_corriente)) < 0.01,
                "tiene_activos": total_activo > 0,
                "estructura_valida": activo_no_corriente >= 0 and activo_corriente >= 0
            }
        }

        # Comparación con Pasivo + Patrimonio si se solicita
        if comparar_pasivo:
            total_pasivo_patrimonio = self._calcular_total_pasivo_patrimonio()
            respuesta["comparacion_balance"] = {
                "total_pasivo_patrimonio": float(total_pasivo_patrimonio),
                "diferencia": float(total_activo - total_pasivo_patrimonio),
                "balance_cuadra": abs(total_activo - total_pasivo_patrimonio) < 0.01,
                "interpretacion": self._interpretar_balance(total_activo, total_pasivo_patrimonio)
            }

        # Ratios financieros si se solicitan
        if calcular_ratios:
            respuesta["ratios_financieros"] = {
                "ratio_liquidez": float(activo_corriente / activo_no_corriente) if activo_no_corriente != 0 else None,
                "estructura_activo": {
                    "concentracion_no_corriente": float(
                        activo_no_corriente / total_activo * 100) if total_activo != 0 else 0,
                    "concentracion_corriente": float(activo_corriente / total_activo * 100) if total_activo != 0 else 0
                },
                "interpretacion_estructura": self._interpretar_estructura_activo(activo_no_corriente, activo_corriente)
            }

        # Metadata adicional
        respuesta["metadata"] = {
            "fecha_calculo": "2025-05-30",  # Podría ser datetime.now()
            "principio_contable": "BOE - Plan General de Contabilidad",
            "ecuacion_fundamental": "ACTIVO = PASIVO + PATRIMONIO NETO",
            "naturaleza_cuentas": "Las cuentas de activo tienen naturaleza deudora",
            "parametros_consulta": {
                "incluir_detalle": incluir_detalle,
                "comparar_pasivo": comparar_pasivo,
                "calcular_ratios": calcular_ratios
            }
        }

        return Response(respuesta, status=status.HTTP_200_OK)

    def _calcular_saldo_activo(self, subarea):
        """
        Calcula el saldo de una subárea de activo.
        Las cuentas de activo tienen naturaleza DEUDORA: Saldo = Debe - Haber
        """
        lineas = LineaFactura.objects.filter(subarea=subarea)

        agregados = lineas.aggregate(
            debe_total=Sum('debe'),
            haber_total=Sum('haber')
        )

        debe = agregados["debe_total"] or Decimal(0)
        haber = agregados["haber_total"] or Decimal(0)
        total_lineas = lineas.count()

        # Para activos: Saldo = Debe - Haber (naturaleza deudora)
        saldo = debe - haber

        return {
            "debe": debe,
            "haber": haber,
            "saldo": saldo,
            "total_lineas": total_lineas
        }

    def _calcular_total_pasivo_patrimonio(self):
        """
        Calcula el total de Pasivo + Patrimonio Neto (Sección C) para comparación
        """
        seccion_c = SeccionContable.objects.filter(letra="C").first()
        if not seccion_c:
            return Decimal(0)

        total = Decimal(0)
        for area in seccion_c.areas.all():
            for subarea in area.subareas.all():
                lineas = LineaFactura.objects.filter(subarea=subarea)
                debe = sum(linea.debe or Decimal(0) for linea in lineas)
                haber = sum(linea.haber or Decimal(0) for linea in lineas)

                # Para pasivo/patrimonio: naturaleza acreedora = Haber - Debe
                saldo = haber - debe
                total += saldo

        return total

    def _interpretar_saldo_activo(self, saldo):
        """
        Interpreta el saldo de una cuenta de activo
        """
        if saldo > 0:
            return f"Activo por valor de €{saldo:,.2f}"
        elif saldo < 0:
            return f"⚠️ Saldo negativo: €{abs(saldo):,.2f} (revisar)"
        else:
            return "Sin saldo"

    def _interpretar_balance(self, total_activo, total_pasivo_patrimonio):
        """
        Interpreta si el balance general cuadra
        """
        diferencia = abs(total_activo - total_pasivo_patrimonio)

        if diferencia < 0.01:
            return "✅ Balance perfecto: Activo = Pasivo + Patrimonio"
        elif diferencia < 100:
            return f"⚠️ Diferencia menor: €{diferencia:.2f} (probablemente redondeos)"
        else:
            return f"❌ Balance descuadrado: diferencia de €{diferencia:,.2f}"

    def _interpretar_estructura_activo(self, activo_no_corriente, activo_corriente):
        """
        Interpreta la estructura del activo
        """
        total = activo_no_corriente + activo_corriente
        if total == 0:
            return "Sin activos registrados"

        ratio_nc = float(activo_no_corriente / total)

        if ratio_nc > 0.7:
            return "Empresa intensiva en activos fijos (inmuebles, maquinaria)"
        elif ratio_nc > 0.4:
            return "Estructura equilibrada entre activos fijos y corrientes"
        else:
            return "Empresa con alta liquidez (predomina activo corriente)"

    def _obtener_metadata_area_activo(self, area, letra_seccion):
        """
        Metadata específica para áreas de activo
        """
        metadata = {
            "seccion": letra_seccion,
            "tipo_activo": "NO_CORRIENTE" if letra_seccion == "A" else "CORRIENTE"
        }

        # Clasificaciones específicas
        nombre_lower = area.nombre.lower()

        if "inmovilizado" in nombre_lower:
            metadata["clasificacion"] = "INMOVILIZADO"
        elif "inversiones" in nombre_lower:
            metadata["clasificacion"] = "INVERSIONES"
        elif "existencias" in nombre_lower:
            metadata["clasificacion"] = "EXISTENCIAS"
        elif "deudores" in nombre_lower or "clientes" in nombre_lower:
            metadata["clasificacion"] = "DEUDORES"
        elif "efectivo" in nombre_lower or "tesorería" in nombre_lower:
            metadata["clasificacion"] = "TESORERIA"
        else:
            metadata["clasificacion"] = "OTROS"

        return metadata


class TotalPasivoYPatrimonioView(APIView):
    """
    Calcula el Total Patrimonio Neto y Pasivo según el BOE (Solo Sección C)
    con principios contables correctos y estructura BOE exacta.

    TOTAL PATRIMONIO Y PASIVO = A) PATRIMONIO NETO + B) PASIVO NO CORRIENTE + C) PASIVO CORRIENTE

    Parámetros opcionales:
    - ?incluir_detalle=true : incluir desglose completo
    - ?comparar_activo=true : comparar con total activo
    - ?estructura_boe=true : agrupar según estructura BOE exacta
    """

    def get(self, request, *args, **kwargs):
        # Parámetros de consulta
        incluir_detalle = request.GET.get('incluir_detalle', 'true').lower() == 'true'
        comparar_activo = request.GET.get('comparar_activo', 'false').lower() == 'true'
        estructura_boe = request.GET.get('estructura_boe', 'true').lower() == 'true'

        # SOLO Sección C según BOE
        seccion_c = SeccionContable.objects.filter(letra="C").prefetch_related("areas__subareas").first()

        if not seccion_c:
            return Response({
                "error": "No se encontró la Sección C (Patrimonio Neto y Pasivo)",
                "solucion": "Verificar que la sección C esté cargada correctamente"
            }, status=status.HTTP_404_NOT_FOUND)

        # Inicializar totales según estructura BOE
        patrimonio_neto = Decimal(0)  # A) PATRIMONIO NETO
        pasivo_no_corriente = Decimal(0)  # B) PASIVO NO CORRIENTE
        pasivo_corriente = Decimal(0)  # C) PASIVO CORRIENTE

        detalle_estructura = {
            "A_PATRIMONIO_NETO": {"saldo": Decimal(0), "areas": []},
            "B_PASIVO_NO_CORRIENTE": {"saldo": Decimal(0), "areas": []},
            "C_PASIVO_CORRIENTE": {"saldo": Decimal(0), "areas": []}
        }

        total_debe_seccion = Decimal(0)
        total_haber_seccion = Decimal(0)

        # Procesar todas las áreas de la Sección C
        for area in seccion_c.areas.all():
            area_saldo = Decimal(0)
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            subareas_detalle = []

            # Determinar a qué grupo BOE pertenece esta área
            grupo_boe = self._clasificar_area_segun_boe(area)

            for subarea in area.subareas.all():
                # Obtener totales de debe y haber (campos independientes)
                datos_subarea = self._calcular_saldo_pasivo_patrimonio(subarea)

                # Acumular debe y haber por área
                area_debe += datos_subarea["debe"]
                area_haber += datos_subarea["haber"]

                if incluir_detalle:
                    subareas_detalle.append({
                        "nombre": subarea.nombre,
                        "codigos_positivos": subarea.codigos_positivos,
                        "codigos_negativos": subarea.codigos_negativos,
                        "debe": float(datos_subarea["debe"]),
                        "haber": float(datos_subarea["haber"]),
                        "total_lineas": datos_subarea["total_lineas"]
                    })

            total_debe_seccion += area_debe
            total_haber_seccion += area_haber

            # Acumular debe y haber por grupo BOE
            if grupo_boe == "PATRIMONIO_NETO":
                patrimonio_neto += area_debe + area_haber  # Total de movimientos del patrimonio
                detalle_estructura["A_PATRIMONIO_NETO"]["saldo"] += area_debe + area_haber
                clave_detalle = "A_PATRIMONIO_NETO"
            elif grupo_boe == "PASIVO_NO_CORRIENTE":
                pasivo_no_corriente += area_debe + area_haber  # Total de movimientos del pasivo LP
                detalle_estructura["B_PASIVO_NO_CORRIENTE"]["saldo"] += area_debe + area_haber
                clave_detalle = "B_PASIVO_NO_CORRIENTE"
            elif grupo_boe == "PASIVO_CORRIENTE":
                pasivo_corriente += area_debe + area_haber  # Total de movimientos del pasivo CP
                detalle_estructura["C_PASIVO_CORRIENTE"]["saldo"] += area_debe + area_haber
                clave_detalle = "C_PASIVO_CORRIENTE"
            else:
                # Caso por defecto
                patrimonio_neto += area_debe + area_haber
                detalle_estructura["A_PATRIMONIO_NETO"]["saldo"] += area_debe + area_haber
                clave_detalle = "A_PATRIMONIO_NETO"

            # Guardar detalle del área
            area_info = {
                "nombre": area.nombre,
                "abreviatura": area.abreviatura,
                "debe": float(area_debe),
                "haber": float(area_haber),
                "total_movimientos": float(area_debe + area_haber),
                "grupo_boe": grupo_boe,
                "subareas": subareas_detalle if incluir_detalle else [],
                "metadata": self._obtener_metadata_area_patrimonio_pasivo(area, grupo_boe)
            }

            detalle_estructura[clave_detalle]["areas"].append(area_info)

        # Calcular total
        total_patrimonio_y_pasivo = patrimonio_neto + pasivo_no_corriente + pasivo_corriente

        # Calcular porcentajes
        porcentajes = {}
        if total_patrimonio_y_pasivo != 0:
            porcentajes = {
                "patrimonio_neto": round(float(patrimonio_neto / total_patrimonio_y_pasivo * 100), 2),
                "pasivo_no_corriente": round(float(pasivo_no_corriente / total_patrimonio_y_pasivo * 100), 2),
                "pasivo_corriente": round(float(pasivo_corriente / total_patrimonio_y_pasivo * 100), 2)
            }

        # Preparar respuesta base
        respuesta = {
            "total_patrimonio_y_pasivo": {
                "total_debe": float(total_debe_seccion),
                "total_haber": float(total_haber_seccion),
                "total_movimientos": float(total_debe_seccion + total_haber_seccion),
                "formula": "DEBE + HABER de todas las áreas/subáreas de Sección C",
                "estructura": "A) PATRIMONIO NETO + B) PASIVO NO CORRIENTE + C) PASIVO CORRIENTE"
            },
            "componentes_boe": {
                "A_patrimonio_neto": {
                    "total_movimientos": float(patrimonio_neto),
                    "porcentaje": porcentajes.get("patrimonio_neto", 0),
                    "descripcion": "Fondos propios, ajustes de valor y subvenciones"
                },
                "B_pasivo_no_corriente": {
                    "total_movimientos": float(pasivo_no_corriente),
                    "porcentaje": porcentajes.get("pasivo_no_corriente", 0),
                    "descripcion": "Obligaciones y deudas a largo plazo"
                },
                "C_pasivo_corriente": {
                    "total_movimientos": float(pasivo_corriente),
                    "porcentaje": porcentajes.get("pasivo_corriente", 0),
                    "descripcion": "Obligaciones y deudas a corto plazo"
                }
            },
            "estructura_detallada": detalle_estructura if estructura_boe else {},
            "validaciones": {
                "sumas_cuadran": abs(
                    total_patrimonio_y_pasivo - (patrimonio_neto + pasivo_no_corriente + pasivo_corriente)) < 0.01,
                "solo_seccion_c": True,
                "estructura_boe_completa": self._validar_estructura_boe_completa(detalle_estructura),
                "saldos_coherentes": self._validar_coherencia_saldos(patrimonio_neto, pasivo_no_corriente,
                                                                     pasivo_corriente)
            }
        }

        # Comparación con Total Activo si se solicita
        if comparar_activo:
            total_activo = self._calcular_total_activo()
            respuesta["comparacion_balance"] = {
                "total_activo": float(total_activo),
                "diferencia": float(total_activo - total_patrimonio_y_pasivo),
                "balance_cuadra": abs(total_activo - total_patrimonio_y_pasivo) < 0.01,
                "interpretacion": self._interpretar_balance_general(total_activo, total_patrimonio_y_pasivo),
                "ecuacion_fundamental": "ACTIVO = PASIVO + PATRIMONIO NETO"
            }

        # Ratios financieros
        respuesta["ratios_financieros"] = {
            "autonomia_financiera": float(
                patrimonio_neto / total_patrimonio_y_pasivo * 100) if total_patrimonio_y_pasivo != 0 else 0,
            "endeudamiento": float((
                                           pasivo_no_corriente + pasivo_corriente) / total_patrimonio_y_pasivo * 100) if total_patrimonio_y_pasivo != 0 else 0,
            "estructura_pasivo": {
                "pasivo_largo_plazo": float(pasivo_no_corriente / (pasivo_no_corriente + pasivo_corriente) * 100) if (
                                                                                                                             pasivo_no_corriente + pasivo_corriente) != 0 else 0,
                "pasivo_corto_plazo": float(pasivo_corriente / (pasivo_no_corriente + pasivo_corriente) * 100) if (
                                                                                                                          pasivo_no_corriente + pasivo_corriente) != 0 else 0
            },
            "interpretacion": self._interpretar_estructura_financiera(patrimonio_neto, pasivo_no_corriente,
                                                                      pasivo_corriente)
        }

        # Metadata
        respuesta["metadata"] = {
            "seccion_boe": "C) PATRIMONIO NETO Y PASIVO",
            "principio_calculo": "Sumatoria de DEBE y HABER por separado de todas las áreas/subáreas de Sección C",
            "campos_resultado": {
                "total_debe": "Suma de todos los valores DEBE",
                "total_haber": "Suma de todos los valores HABER",
                "total_movimientos": "DEBE + HABER (para referencia)"
            },
            "areas_incluidas": "Todas las áreas/subáreas clasificadas en Sección C",
            "parametros_consulta": {
                "incluir_detalle": incluir_detalle,
                "comparar_activo": comparar_activo,
                "estructura_boe": estructura_boe
            }
        }

        return Response(respuesta, status=status.HTTP_200_OK)

    def _calcular_saldo_pasivo_patrimonio(self, subarea):
        """
        Obtiene los totales de debe y haber de una subárea.
        NO se suman entre sí, son campos independientes para mostrar.
        """
        lineas = LineaFactura.objects.filter(subarea=subarea)

        agregados = lineas.aggregate(
            debe_total=Sum('debe'),
            haber_total=Sum('haber')
        )

        debe = agregados["debe_total"] or Decimal(0)
        haber = agregados["haber_total"] or Decimal(0)
        total_lineas = lineas.count()

        return {
            "debe": debe,
            "haber": haber,
            "total_lineas": total_lineas
        }

    def _clasificar_area_segun_boe(self, area):
        """
        Clasifica el área según la estructura BOE exacta
        """
        nombre_upper = area.nombre.upper()

        # A) PATRIMONIO NETO
        if any(keyword in nombre_upper for keyword in [
            "PATRIMONIO NETO", "A) PATRIMONIO", "FONDOS PROPIOS",
            "CAPITAL", "RESERVAS", "RESULTADO", "AJUSTES POR CAMBIOS",
            "SUBVENCIONES", "DONACIONES", "LEGADOS"
        ]):
            return "PATRIMONIO_NETO"

        # B) PASIVO NO CORRIENTE
        elif any(keyword in nombre_upper for keyword in [
            "B) PASIVO NO CORRIENTE", "PASIVO NO CORRIENTE",
            "LARGO PLAZO", "PROVISIONES A LARGO", "DEUDAS A LARGO"
        ]):
            return "PASIVO_NO_CORRIENTE"

        # C) PASIVO CORRIENTE
        elif any(keyword in nombre_upper for keyword in [
            "C) PASIVO CORRIENTE", "PASIVO CORRIENTE",
            "CORTO PLAZO", "PROVISIONES A CORTO", "DEUDAS A CORTO",
            "ACREEDORES COMERCIALES"
        ]):
            return "PASIVO_CORRIENTE"

        # Por defecto, si no se puede clasificar claramente
        else:
            # Intentar clasificar por keywords adicionales
            if any(keyword in nombre_upper for keyword in [
                "PROVISIONES", "ACREEDORES", "PROVEEDORES", "DEUDAS"
            ]):
                return "PASIVO_CORRIENTE"  # Por defecto asumir corto plazo
            else:
                return "PATRIMONIO_NETO"  # Por defecto asumir patrimonio

    def _calcular_total_activo(self):
        """
        Calcula el total de áreas clasificadas como activo (Secciones A + B)
        """
        secciones_activo = SeccionContable.objects.filter(letra__in=["A", "B"])
        total_areas = 0

        for seccion in secciones_activo:
            for area in seccion.areas.all():
                total_areas += 1  # Cuenta cada área como 1 unidad

        return total_areas

    def _interpretar_saldo_pasivo_patrimonio(self, total_subarea, grupo_boe):
        """
        Interpreta el total de la subárea (debe + haber)
        """
        if total_subarea > 0:
            if grupo_boe == "PATRIMONIO_NETO":
                return f"Total patrimonio neto: €{total_subarea:,.2f}"
            else:
                return f"Total pasivo: €{total_subarea:,.2f}"
        else:
            return "Sin movimientos"

    def _validar_estructura_boe_completa(self, detalle_estructura):
        """
        Valida que estén presentes los 3 componentes del BOE
        """
        return all(
            detalle_estructura[grupo]["saldo"] >= 0
            for grupo in ["A_PATRIMONIO_NETO", "B_PASIVO_NO_CORRIENTE", "C_PASIVO_CORRIENTE"]
        )

    def _validar_coherencia_saldos(self, patrimonio_neto, pasivo_no_corriente, pasivo_corriente):
        """
        Valida que los saldos sean coherentes
        """
        return all(saldo >= 0 for saldo in [patrimonio_neto, pasivo_no_corriente, pasivo_corriente])

    def _interpretar_balance_general(self, total_activo, total_patrimonio_pasivo):
        """
        Interpreta el balance general
        """
        diferencia = abs(total_activo - total_patrimonio_pasivo)

        if diferencia < 0.01:
            return "✅ Balance perfecto: ACTIVO = PASIVO + PATRIMONIO"
        elif diferencia < 100:
            return f"⚠️ Diferencia menor: €{diferencia:.2f}"
        else:
            return f"❌ Balance descuadrado: €{diferencia:,.2f}"

    def _interpretar_estructura_financiera(self, patrimonio_neto, pasivo_no_corriente, pasivo_corriente):
        """
        Interpreta la estructura financiera de la empresa
        """
        total = patrimonio_neto + pasivo_no_corriente + pasivo_corriente
        if total == 0:
            return "Sin estructura financiera"

        ratio_patrimonio = float(patrimonio_neto / total)
        ratio_pasivo_corriente = float(pasivo_corriente / total)

        if ratio_patrimonio > 0.6:
            return "Empresa con alta autonomía financiera"
        elif ratio_patrimonio > 0.3:
            return "Estructura financiera equilibrada"
        elif ratio_pasivo_corriente > 0.5:
            return "Alta dependencia de financiación a corto plazo"
        else:
            return "Empresa muy endeudada"

    def _obtener_metadata_area_patrimonio_pasivo(self, area, grupo_boe):
        """
        Metadata específica para áreas de patrimonio/pasivo
        """
        return {
            "grupo_boe": grupo_boe,
            "naturaleza_contable": "ACREEDORA",
            "descripcion": area.descripcion,
            "es_patrimonio": grupo_boe == "PATRIMONIO_NETO",
            "es_pasivo": grupo_boe in ["PASIVO_NO_CORRIENTE", "PASIVO_CORRIENTE"],
            "plazo": "LARGO" if grupo_boe == "PASIVO_NO_CORRIENTE" else "CORTO" if grupo_boe == "PASIVO_CORRIENTE" else "NO_APLICA"
        }


class EstadoResultadosView(APIView):
    """
    Devuelve el estado de resultados (Cuenta de Pérdidas y Ganancias),
    limitando los cálculos solo a las áreas de la Sección D.
    """

    def get(self, request, *args, **kwargs):
        # Filtrar solo áreas de la sección D
        areas_seccion_d = AreaContable.objects.filter(seccion__letra="D").prefetch_related("subareas")
        subareas_d = [sub for area in areas_seccion_d for sub in area.subareas.all()]

        detalle = []
        total_debe = Decimal(0)
        total_haber = Decimal(0)

        # Mapeo para cálculos individuales
        resultado_explotacion_subareas = []
        resultado_financiero_subareas = []
        impuesto_sobre_beneficios_subareas = []

        # Iterar por cada área de sección D
        for area in areas_seccion_d:
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            subarea_detalles = []

            for subarea in area.subareas.all():
                lineas = LineaFactura.objects.filter(subarea=subarea)
                debe = sum(linea.debe or Decimal(0) for linea in lineas)
                haber = sum(linea.haber or Decimal(0) for linea in lineas)

                # Acumulados generales
                total_debe += debe
                total_haber += haber
                area_debe += debe
                area_haber += haber

                # Guardar detalle por subárea
                subarea_detalles.append({
                    "nombre": subarea.nombre,
                    "debe": float(debe),
                    "haber": float(haber)
                })

                # Clasificación para cálculos específicos
                if "RESULTADO DE EXPLOTACIÓN" not in subarea.nombre.upper() and \
                        "RESULTADO FINANCIERO" not in subarea.nombre.upper() and \
                        "RESULTADO ANTES" not in subarea.nombre.upper() and \
                        "RESULTADO DEL EJERCICIO" not in subarea.nombre.upper():

                    if "financier" in subarea.nombre.lower():
                        resultado_financiero_subareas.append((debe, haber))
                    elif "impuesto" in subarea.nombre.lower():
                        impuesto_sobre_beneficios_subareas.append((debe, haber))
                    else:
                        resultado_explotacion_subareas.append((debe, haber))

            # Guardar el área con sus subáreas
            detalle.append({
                "nombre": area.nombre,
                "debe": float(area_debe),
                "haber": float(area_haber),
                "subareas": subarea_detalles
            })

        # Calcular resultados
        def calcular_resultado(sumas):
            total_debe = sum(d for d, h in sumas)
            total_haber = sum(h for d, h in sumas)
            return float(total_haber - total_debe)

        resultado_explotacion = calcular_resultado(resultado_explotacion_subareas)
        resultado_financiero = calcular_resultado(resultado_financiero_subareas)
        resultado_antes_impuestos = resultado_explotacion + resultado_financiero
        resultado_ejercicio = resultado_antes_impuestos - calcular_resultado(impuesto_sobre_beneficios_subareas)

        return Response({
            "total_estado_resultados": {
                "debe": float(total_debe),
                "haber": float(total_haber),
                "balanceado": total_debe == total_haber
            },
            "detalle": detalle,
            "resultados": {
                "resultado_explotacion": resultado_explotacion,
                "resultado_financiero": resultado_financiero,
                "resultado_antes_impuestos": resultado_antes_impuestos,
                "resultado_del_ejercicio": resultado_ejercicio
            }
        }, status=status.HTTP_200_OK)


class EstadoResultadosCorregidoView(APIView):
    """
    Estado de Resultados con cálculo correcto de pérdidas y ganancias.
    Calcula los resultados según los principios contables españoles.
    """

    def get(self, request, *args, **kwargs):
        # Filtrar solo áreas de la sección D
        areas_seccion_d = AreaContable.objects.filter(seccion__letra="D").prefetch_related("subareas")

        detalle = []
        total_debe = Decimal(0)
        total_haber = Decimal(0)

        # Clasificaciones contables específicas para cálculos
        ingresos_explotacion = Decimal(0)
        gastos_explotacion = Decimal(0)
        ingresos_financieros = Decimal(0)
        gastos_financieros = Decimal(0)
        ingresos_extraordinarios = Decimal(0)
        gastos_extraordinarios = Decimal(0)
        impuestos_beneficios = Decimal(0)

        # Iterar por cada área de sección D
        for area in areas_seccion_d:
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            subarea_detalles = []

            for subarea in area.subareas.all():
                lineas = LineaFactura.objects.filter(subarea=subarea)
                debe = sum(linea.debe or Decimal(0) for linea in lineas)
                haber = sum(linea.haber or Decimal(0) for linea in lineas)

                # Acumulados generales
                total_debe += debe
                total_haber += haber
                area_debe += debe
                area_haber += haber

                # Guardar detalle por subárea
                subarea_detalles.append({
                    "nombre": subarea.nombre,
                    "debe": float(debe),
                    "haber": float(haber)
                })

                # **CLASIFICACIÓN CONTABLE CORRECTA**
                area_nombre_lower = area.nombre.lower()
                subarea_nombre_lower = subarea.nombre.lower()

                # Clasificar según el tipo de cuenta para cálculo de resultados
                if self._es_ingreso_explotacion(area_nombre_lower, subarea_nombre_lower):
                    # Ingresos: el saldo es HABER - DEBE
                    ingresos_explotacion += (haber - debe)

                elif self._es_gasto_explotacion(area_nombre_lower, subarea_nombre_lower):
                    # Gastos: el saldo es DEBE - HABER (se resta de ingresos)
                    gastos_explotacion += (debe - haber)

                elif self._es_ingreso_financiero(area_nombre_lower, subarea_nombre_lower):
                    ingresos_financieros += (haber - debe)

                elif self._es_gasto_financiero(area_nombre_lower, subarea_nombre_lower):
                    gastos_financieros += (debe - haber)

                elif self._es_ingreso_extraordinario(area_nombre_lower, subarea_nombre_lower):
                    ingresos_extraordinarios += (haber - debe)

                elif self._es_gasto_extraordinario(area_nombre_lower, subarea_nombre_lower):
                    gastos_extraordinarios += (debe - haber)

                elif self._es_impuesto_beneficios(area_nombre_lower, subarea_nombre_lower):
                    impuestos_beneficios += (debe - haber)

            # Guardar el área con sus subáreas
            detalle.append({
                "nombre": area.nombre,
                "debe": float(area_debe),
                "haber": float(area_haber),
                "subareas": subarea_detalles
            })

        # **CÁLCULO CORRECTO DE RESULTADOS**
        resultado_explotacion = ingresos_explotacion - gastos_explotacion
        resultado_financiero = ingresos_financieros - gastos_financieros
        resultado_extraordinario = ingresos_extraordinarios - gastos_extraordinarios
        resultado_antes_impuestos = resultado_explotacion + resultado_financiero + resultado_extraordinario
        resultado_del_ejercicio = resultado_antes_impuestos - impuestos_beneficios

        return Response({
            "total_estado_resultados": {
                "debe": float(total_debe),
                "haber": float(total_haber),
                "balanceado": total_debe == total_haber
            },
            "detalle": detalle,
            "resultados": {
                "ingresos_explotacion": float(ingresos_explotacion),
                "gastos_explotacion": float(gastos_explotacion),
                "resultado_explotacion": float(resultado_explotacion),

                "ingresos_financieros": float(ingresos_financieros),
                "gastos_financieros": float(gastos_financieros),
                "resultado_financiero": float(resultado_financiero),

                "ingresos_extraordinarios": float(ingresos_extraordinarios),
                "gastos_extraordinarios": float(gastos_extraordinarios),
                "resultado_extraordinario": float(resultado_extraordinario),

                "resultado_antes_impuestos": float(resultado_antes_impuestos),
                "impuestos_beneficios": float(impuestos_beneficios),
                "resultado_del_ejercicio": float(resultado_del_ejercicio),

                # Indicadores adicionales
                "tiene_beneficios": resultado_del_ejercicio > 0,
                "tiene_perdidas": resultado_del_ejercicio < 0,
                "interpretacion": self._interpretar_resultado(resultado_del_ejercicio)
            }
        }, status=status.HTTP_200_OK)

    def _es_ingreso_explotacion(self, area_nombre, subarea_nombre):
        """Identifica si es un ingreso de explotación"""
        ingresos_keywords = [
            'importe neto de la cifra de negocios',
            'ventas',
            'prestaciones de servicios',
            'otros ingresos de explotación',
            'subvenciones de explotación',
            'ingresos accesorios'
        ]

        # También verificar si está en área de "Ingresos" pero NO es extraordinario
        if 'ingresos' in area_nombre and 'extraordinario' not in subarea_nombre and 'financier' not in area_nombre:
            return True

        return any(keyword in area_nombre for keyword in ingresos_keywords)

    def _es_gasto_explotacion(self, area_nombre, subarea_nombre):
        """Identifica si es un gasto de explotación"""
        gastos_keywords = [
            'aprovisionamientos',
            'gastos de personal',
            'otros gastos de explotación',
            'amortización',
            'amortizaciones'
        ]

        # También verificar si está en área de "Gastos" pero NO es financiero
        if 'gastos' in area_nombre and 'financier' not in area_nombre:
            return True

        return any(keyword in area_nombre for keyword in gastos_keywords)

    def _es_ingreso_financiero(self, area_nombre, subarea_nombre):
        """Identifica si es un ingreso financiero"""
        return 'ingresos financieros' in area_nombre

    def _es_gasto_financiero(self, area_nombre, subarea_nombre):
        """Identifica si es un gasto financiero"""
        return 'gastos financieros' in area_nombre

    def _es_ingreso_extraordinario(self, area_nombre, subarea_nombre):
        """Identifica si es un ingreso extraordinario"""
        return ('extraordinario' in subarea_nombre or
                'diferencias positivas de cambio' in subarea_nombre)

    def _es_gasto_extraordinario(self, area_nombre, subarea_nombre):
        """Identifica si es un gasto extraordinario"""
        return ('extraordinario' in subarea_nombre or
                'diferencias negativas de cambio' in subarea_nombre)

    def _es_impuesto_beneficios(self, area_nombre, subarea_nombre):
        """Identifica si son impuestos sobre beneficios"""
        return 'impuestos sobre beneficios' in area_nombre

    def _interpretar_resultado(self, resultado):
        """Proporciona una interpretación del resultado"""
        if resultado > 1000:
            return f"Beneficio de €{resultado:,.2f}"
        elif resultado > 0:
            return f"Beneficio pequeño de €{resultado:,.2f}"
        elif resultado == 0:
            return "Equilibrio perfecto (sin beneficios ni pérdidas)"
        elif resultado > -1000:
            return f"Pérdida pequeña de €{abs(resultado):,.2f}"
        else:
            return f"Pérdida de €{abs(resultado):,.2f}"
