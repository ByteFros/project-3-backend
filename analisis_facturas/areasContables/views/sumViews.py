from ..models import SeccionContable, AreaContable, SubAreaContable, LineaFactura
import re
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.db.models import Sum
from areasContables.utils.codigos_boe import ACTIVO_NO_CORRIENTE, ACTIVO_CORRIENTE



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



class TotalActivoCodigosView(APIView):
    """
    Calcula el Total Activo basado en los códigos definidos en utils/codigos_boe.py,
    sin depender de modelos Seccion/Area/Subarea en base de datos.
    """

    def get(self, request, *args, **kwargs):
        incluir_detalle = request.GET.get('incluir_detalle', 'true').lower() == 'true'

        total_activo = Decimal(0)
        total_debe = Decimal(0)
        total_haber = Decimal(0)
        detalle_secciones = []

        for letra, seccion_data in [("A", ACTIVO_NO_CORRIENTE), ("B", ACTIVO_CORRIENTE)]:
            seccion_saldo = Decimal(0)
            seccion_debe = Decimal(0)
            seccion_haber = Decimal(0)
            areas_detalle = []

            for nombre_area, area_data in seccion_data.items():
                area_saldo = Decimal(0)
                area_debe = Decimal(0)
                area_haber = Decimal(0)
                subareas_detalle = []

                for nombre_subarea, codigos in area_data["subareas"].items():
                    resultado = self._calcular_saldo_por_codigos(codigos)
                    area_saldo += resultado["saldo"]
                    area_debe += resultado["debe"]
                    area_haber += resultado["haber"]

                    if incluir_detalle:
                        subareas_detalle.append({
                            "nombre": nombre_subarea,
                            "debe": float(resultado["debe"]),
                            "haber": float(resultado["haber"]),
                            "saldo": float(resultado["saldo"]),
                            "total_lineas": resultado["total_lineas"]
                        })

                seccion_saldo += area_saldo
                seccion_debe += area_debe
                seccion_haber += area_haber

                if incluir_detalle:
                    areas_detalle.append({
                        "nombre": nombre_area,
                        "saldo": float(area_saldo),
                        "debe": float(area_debe),
                        "haber": float(area_haber),
                        "subareas": subareas_detalle
                    })

            detalle_secciones.append({
                "letra": letra,
                "nombre": "Activo no corriente" if letra == "A" else "Activo corriente",
                "saldo": float(seccion_saldo),
                "debe": float(seccion_debe),
                "haber": float(seccion_haber),
                "areas": areas_detalle
            })

            total_activo += seccion_saldo
            total_debe += seccion_debe
            total_haber += seccion_haber

        respuesta = {
            "total_activo": {
                "saldo": float(total_activo),
                "debe_total": float(total_debe),
                "haber_total": float(total_haber),
                "formula": "ACTIVO NO CORRIENTE + ACTIVO CORRIENTE"
            },
            "detalle_por_seccion": detalle_secciones,
            "validaciones": {
                "sumas_cuadran": abs(total_activo - (total_debe - total_haber)) < 0.01,
                "tiene_activos": total_activo > 0
            }
        }

        return Response(respuesta, status=status.HTTP_200_OK)



    def _calcular_saldo_por_codigos(self, codigos):
        sumar = codigos.get("sumar", [])
        restar = codigos.get("restar", [])

        # Acumuladores para valores finales
        debe_total = Decimal(0)
        haber_total = Decimal(0)
        count_total = 0

        # Procesar códigos a SUMAR: agregar sus valores al total
        for codigo in sumar:
            lineas = LineaFactura.objects.filter(cuenta__startswith=str(codigo))
            debe_total += lineas.aggregate(total=Sum("debe"))["total"] or Decimal(0)
            haber_total += lineas.aggregate(total=Sum("haber"))["total"] or Decimal(0)
            count_total += lineas.count()

        # Procesar códigos a RESTAR: restar sus valores del total
        for codigo in restar:
            lineas = LineaFactura.objects.filter(cuenta__startswith=str(codigo))
            debe_restar = lineas.aggregate(total=Sum("debe"))["total"] or Decimal(0)
            haber_restar = lineas.aggregate(total=Sum("haber"))["total"] or Decimal(0)
            
            # RESTAR estos valores del total (como correctores)
            debe_total -= debe_restar
            haber_total -= haber_restar
            count_total += lineas.count()

        # El saldo es simplemente debe menos haber (naturaleza de activo)
        saldo_total = debe_total - haber_total

        return {
            "debe": debe_total,
            "haber": haber_total,
            "saldo": saldo_total,
            "total_lineas": count_total
        }



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
    Calcula el Total Patrimonio Neto y Pasivo según el BOE
    """

    def get(self, request, *args, **kwargs):
        incluir_detalle = request.GET.get('incluir_detalle', 'true').lower() == 'true'
        comparar_activo = request.GET.get('comparar_activo', 'false').lower() == 'true'
        estructura_boe = request.GET.get('estructura_boe', 'true').lower() == 'true'

        secciones = SeccionContable.objects.filter(letra__in=["C", "D", "E"]).prefetch_related("areas__subareas")

        patrimonio_neto = Decimal(0)
        pasivo_no_corriente = Decimal(0)
        pasivo_corriente = Decimal(0)

        detalle_estructura = {
            "A_PATRIMONIO_NETO": {"saldo": Decimal(0), "areas": []},
            "B_PASIVO_NO_CORRIENTE": {"saldo": Decimal(0), "areas": []},
            "C_PASIVO_CORRIENTE": {"saldo": Decimal(0), "areas": []}
        }

        total_debe = Decimal(0)
        total_haber = Decimal(0)

        for seccion in secciones:
            letra = seccion.letra
            for area in seccion.areas.all():
                area_debe = Decimal(0)
                area_haber = Decimal(0)
                subareas_detalle = []

                for subarea in area.subareas.all():
                    datos = self._calcular_saldo(subarea)
                    area_debe += datos["debe"]
                    area_haber += datos["haber"]

                    if incluir_detalle:
                        subareas_detalle.append({
                            "nombre": subarea.nombre,
                            "codigos_positivos": subarea.codigos_positivos,
                            "codigos_negativos": subarea.codigos_negativos,
                            "debe": float(datos["debe"]),
                            "haber": float(datos["haber"]),
                            "total_lineas": datos["total_lineas"]
                        })

                total_debe += area_debe
                total_haber += area_haber
                total_mov = area_debe + area_haber

                area_info = {
                    "nombre": area.nombre,
                    "abreviatura": area.abreviatura,
                    "debe": float(area_debe),
                    "haber": float(area_haber),
                    "total_movimientos": float(total_mov),
                    "subareas": subareas_detalle if incluir_detalle else []
                }

                if letra == "C":
                    patrimonio_neto += total_mov
                    detalle_estructura["A_PATRIMONIO_NETO"]["saldo"] += total_mov
                    detalle_estructura["A_PATRIMONIO_NETO"]["areas"].append(area_info)
                elif letra == "D":
                    pasivo_no_corriente += total_mov
                    detalle_estructura["B_PASIVO_NO_CORRIENTE"]["saldo"] += total_mov
                    detalle_estructura["B_PASIVO_NO_CORRIENTE"]["areas"].append(area_info)
                elif letra == "E":
                    pasivo_corriente += total_mov
                    detalle_estructura["C_PASIVO_CORRIENTE"]["saldo"] += total_mov
                    detalle_estructura["C_PASIVO_CORRIENTE"]["areas"].append(area_info)

        total_pp = patrimonio_neto + pasivo_no_corriente + pasivo_corriente
        porcentaje = lambda val: round(float(val / total_pp * 100), 2) if total_pp else 0

        respuesta = {
            "total_patrimonio_y_pasivo": {
                "total_debe": float(total_debe),
                "total_haber": float(total_haber),
                "total_movimientos": float(total_debe + total_haber),
                "estructura": "A) PATRIMONIO NETO + B) PASIVO NO CORRIENTE + C) PASIVO CORRIENTE"
            },
            "componentes_boe": {
                "A_patrimonio_neto": {
                    "total_movimientos": float(patrimonio_neto),
                    "porcentaje": porcentaje(patrimonio_neto)
                },
                "B_pasivo_no_corriente": {
                    "total_movimientos": float(pasivo_no_corriente),
                    "porcentaje": porcentaje(pasivo_no_corriente)
                },
                "C_pasivo_corriente": {
                    "total_movimientos": float(pasivo_corriente),
                    "porcentaje": porcentaje(pasivo_corriente)
                }
            },
            "estructura_detallada": detalle_estructura if estructura_boe else {},
            "validaciones": {
                "estructura_completa": all([
                    patrimonio_neto >= 0,
                    pasivo_no_corriente >= 0,
                    pasivo_corriente >= 0
                ])
            }
        }

        if comparar_activo:
            total_activo = self._calcular_total_activo()
            respuesta["comparacion_balance"] = {
                "total_activo": float(total_activo),
                "total_pasivo_patrimonio": float(total_pp),
                "diferencia": float(total_activo - total_pp),
                "balance_cuadra": abs(total_activo - total_pp) < 0.01
            }

        return Response(respuesta)

    def _calcular_saldo(self, subarea):
        lineas = LineaFactura.objects.filter(subarea=subarea)
        agregados = lineas.aggregate(
            debe_total=Sum('debe'),
            haber_total=Sum('haber')
        )
        return {
            "debe": agregados["debe_total"] or Decimal(0),
            "haber": agregados["haber_total"] or Decimal(0),
            "total_lineas": lineas.count()
        }

    def _calcular_total_activo(self):
        secciones = SeccionContable.objects.filter(letra__in=["A", "B"])
        total = Decimal(0)
        for seccion in secciones:
            for area in seccion.areas.all():
                for subarea in area.subareas.all():
                    lineas = LineaFactura.objects.filter(subarea=subarea)
                    datos = lineas.aggregate(
                        debe_total=Sum("debe"),
                        haber_total=Sum("haber")
                    )
                    total += (datos["debe_total"] or Decimal(0)) - (datos["haber_total"] or Decimal(0))
        return total


class IngresosGastosReconocidosView(APIView):
    """
    Calcula el total de ingresos y gastos reconocidos (Sección G) según BOE.
    Incluye ingresos imputados directamente al patrimonio neto y transferencias a PyG.
    """

    def get(self, request, *args, **kwargs):
        areas_g = AreaContable.objects.filter(seccion__letra="G").prefetch_related("subareas")

        total_ingresos = Decimal(0)
        total_gastos = Decimal(0)
        detalle = []

        for area in areas_g:
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            subarea_detalles = []

            for subarea in area.subareas.all():
                lineas = LineaFactura.objects.filter(subarea=subarea)
                debe = sum(linea.debe or Decimal(0) for linea in lineas)
                haber = sum(linea.haber or Decimal(0) for linea in lineas)

                area_debe += debe
                area_haber += haber

                subarea_detalles.append({
                    "nombre": subarea.nombre,
                    "debe": float(debe),
                    "haber": float(haber)
                })

            total_ingresos += area_haber
            total_gastos += area_debe

            detalle.append({
                "nombre": area.nombre,
                "debe": float(area_debe),
                "haber": float(area_haber),
                "subareas": subarea_detalles
            })

        resultado_final = total_ingresos - total_gastos

        return Response({
            "total_ingresos_y_gastos_reconocidos": {
                "debe": float(total_gastos),
                "haber": float(total_ingresos),
                "resultado": float(resultado_final),
                "interpretacion": self._interpretar_resultado(resultado_final)
            },
            "detalle": detalle
        }, status=status.HTTP_200_OK)

    def _interpretar_resultado(self, resultado):
        if resultado > 1000:
            return f"Reconocimiento positivo de €{resultado:,.2f}"
        elif resultado > 0:
            return f"Ligero reconocimiento positivo de €{resultado:,.2f}"
        elif resultado == 0:
            return "Sin impacto reconocido"
        elif resultado > -1000:
            return f"Ligera pérdida reconocida de €{abs(resultado):,.2f}"
        else:
            return f"Pérdida reconocida de €{abs(resultado):,.2f}"


class EstadoResultadosCorregidoView(APIView):
    """
    Estado de Resultados con cálculo correcto de pérdidas y ganancias.
    Calcula los resultados según los principios contables españoles y la estructura del BOE.
    """

    def get(self, request, *args, **kwargs):
        # Filtrar áreas de la sección F (Cuenta de Pérdidas y Ganancias)
        areas_seccion_f = AreaContable.objects.filter(seccion__letra="F").prefetch_related("subareas")

        detalle = []
        total_debe = Decimal(0)
        total_haber = Decimal(0)

        # Definir áreas por ID según el BOE y tu estructura
        INGRESOS_EXPLOTACION_IDS = [94, 95, 96, 98, 102, 103]  # Áreas que generan ingresos
        GASTOS_EXPLOTACION_IDS = [97, 99, 100, 101, 104]  # Áreas que generan gastos
        INGRESOS_FINANCIEROS_IDS = [105]  # Ingresos financieros
        GASTOS_FINANCIEROS_IDS = [106]  # Gastos financieros
        EXTRAORDINARIOS_IDS = [107, 108, 109]  # Resultados extraordinarios
        IMPUESTOS_IDS = [110]  # Impuestos sobre beneficios

        # Variables para cálculos de resultados
        ingresos_explotacion = Decimal(0)
        gastos_explotacion = Decimal(0)
        ingresos_financieros = Decimal(0)
        gastos_financieros = Decimal(0)
        ingresos_extraordinarios = Decimal(0)
        gastos_extraordinarios = Decimal(0)
        impuestos_beneficios = Decimal(0)

        # Iterar por cada área de sección F
        for area in areas_seccion_f:
            area_debe = Decimal(0)
            area_haber = Decimal(0)
            subarea_detalles = []

            for subarea in area.subareas.all():
                # Calcular movimientos por códigos positivos y negativos
                debe_subarea, haber_subarea = self._calcular_movimientos_subarea(subarea)

                # Acumulados generales
                total_debe += debe_subarea
                total_haber += haber_subarea
                area_debe += debe_subarea
                area_haber += haber_subarea

                # Guardar detalle por subárea
                subarea_detalles.append({
                    "nombre": subarea.nombre,
                    "debe": float(debe_subarea),
                    "haber": float(haber_subarea)
                })

            # Clasificar según el ID del área para cálculo de resultados
            saldo_area = self._calcular_saldo_area(area)

            if area.id in INGRESOS_EXPLOTACION_IDS:
                ingresos_explotacion += saldo_area
            elif area.id in GASTOS_EXPLOTACION_IDS:
                gastos_explotacion += abs(saldo_area)  # Los gastos siempre positivos para el cálculo
            elif area.id in INGRESOS_FINANCIEROS_IDS:
                ingresos_financieros += saldo_area
            elif area.id in GASTOS_FINANCIEROS_IDS:
                gastos_financieros += abs(saldo_area)
            elif area.id in EXTRAORDINARIOS_IDS:
                # Los extraordinarios pueden ser ingresos o gastos
                if saldo_area >= 0:
                    ingresos_extraordinarios += saldo_area
                else:
                    gastos_extraordinarios += abs(saldo_area)
            elif area.id in IMPUESTOS_IDS:
                impuestos_beneficios += abs(saldo_area)

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

    def _calcular_movimientos_subarea(self, subarea):
        """Calcula los movimientos de una subárea usando códigos positivos y negativos"""
        debe_total = Decimal(0)
        haber_total = Decimal(0)

        # Procesar códigos positivos
        if subarea.codigos_positivos:
            codigos_pos = [c.strip() for c in subarea.codigos_positivos.split(',') if c.strip()]
            for codigo in codigos_pos:
                lineas = LineaFactura.objects.filter(subarea=subarea, cuenta__startswith=codigo)
                for linea in lineas:
                    debe_total += linea.debe or Decimal(0)
                    haber_total += linea.haber or Decimal(0)

        # Procesar códigos negativos (se restan)
        if subarea.codigos_negativos:
            codigos_neg = [c.strip() for c in subarea.codigos_negativos.split(',') if c.strip()]
            for codigo in codigos_neg:
                lineas = LineaFactura.objects.filter(subarea=subarea, cuenta__startswith=codigo)
                for linea in lineas:
                    # Los códigos negativos se restan, pero mantenemos el debe/haber por separado
                    debe_total += linea.haber or Decimal(0)  # Invertimos para restar
                    haber_total += linea.debe or Decimal(0)  # Invertimos para restar

        return debe_total, haber_total

    def _calcular_saldo_area(self, area):
        """Calcula el saldo neto de un área según el tipo de cuenta contable"""
        saldo_total = Decimal(0)

        for subarea in area.subareas.all():
            # Códigos positivos: suman al saldo
            if subarea.codigos_positivos:
                codigos_pos = [c.strip() for c in subarea.codigos_positivos.split(',') if c.strip()]
                for codigo in codigos_pos:
                    lineas = LineaFactura.objects.filter(subarea=subarea, cuenta__startswith=codigo)
                    for linea in lineas:
                        debe = linea.debe or Decimal(0)
                        haber = linea.haber or Decimal(0)

                        # Determinar si es cuenta de ingreso o gasto por el código
                        if self._es_cuenta_ingreso(codigo):
                            saldo_total += haber  # Ingresos: solo el haber cuenta
                        else:
                            saldo_total += debe  # Gastos: solo el debe cuenta

            # Códigos negativos: restan del saldo
            if subarea.codigos_negativos:
                codigos_neg = [c.strip() for c in subarea.codigos_negativos.split(',') if c.strip()]
                for codigo in codigos_neg:
                    lineas = LineaFactura.objects.filter(subarea=subarea, cuenta__startswith=codigo)
                    for linea in lineas:
                        debe = linea.debe or Decimal(0)
                        haber = linea.haber or Decimal(0)

                        # Los códigos negativos siempre restan
                        if self._es_cuenta_ingreso(codigo):
                            saldo_total -= haber
                        else:
                            saldo_total -= debe

        return saldo_total

    def _es_cuenta_ingreso(self, codigo):
        """Determina si un código de cuenta es de ingreso (7xx) o gasto (6xx)"""
        try:
            codigo_num = int(codigo)
            return 700 <= codigo_num <= 799  # Cuentas de ingresos (grupo 7)
        except:
            return codigo.startswith('7')  # Fallback para códigos no numéricos

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