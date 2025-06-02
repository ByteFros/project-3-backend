# utils/codigos_boe.py

ACTIVO_NO_CORRIENTE = {
    "Inmovilizado intangible": {
        "subareas": {
            "Desarrollo": {
                "sumar": ["201"],
                "restar": ["2801", "2901"]
            },
            "Concesiones": {
                "sumar": ["202"],
                "restar": ["2802", "2902"]
            },
            "Patentes, licencias, marcas y similares": {
                "sumar": ["203"],
                "restar": ["2803", "2903"]
            },
            "Fondo de comercio": {
                "sumar": ["204"],
                "restar": ["2804"]
            },
            "Aplicaciones informáticas": {
                "sumar": ["206"],
                "restar": ["2806", "2906"]
            },
            "Otro inmovilizado intangible": {
                "sumar": ["205", "209"],
                "restar": ["2805", "2905"]
            }
        }
    },
    "Inmovilizado material": {
        "subareas": {
            "Terrenos y construcciones": {
                "sumar": ["210", "211"],
                "restar": ["2811", "2910", "2911"]
            },
            "Instalaciones técnicas y otro inmovilizado": {
                "sumar": ["212", "213", "214", "215", "216", "217", "218", "219"],
                "restar": ["2812", "2813", "2814", "2815", "2816", "2817", "2818", "2819",
                           "2912", "2913", "2914", "2915", "2916", "2917", "2918", "2919"]
            },
            "Inmovilizado en curso y anticipos": {
                "sumar": ["23"],
                "restar": []
            }
        }
    }
}


ACTIVO_CORRIENTE = {
    "Activos mantenidos para la venta": {
        "subareas": {
            "Activos disponibles para la venta": {
                "sumar": ["580", "581", "582", "583", "584"],
                "restar": ["599"]
            }
        }
    },
    "Existencias": {
        "subareas": {
            "Comerciales": {
                "sumar": ["30"],
                "restar": ["390"]
            },
            "Materias primas y otros aprovisionamientos": {
                "sumar": ["31", "32"],
                "restar": ["391", "392"]
            },
            "Productos en curso": {
                "sumar": ["33", "34"],
                "restar": ["393", "394"]
            },
            "Productos terminados": {
                "sumar": ["35"],
                "restar": ["395"]
            },
            "Subproductos, residuos y materiales recuperados": {
                "sumar": ["36"],
                "restar": ["396"]
            },
            "Anticipos a proveedores": {
                "sumar": ["407"],
                "restar": []
            }
        }
    },
    "Deudores comerciales y otras cuentas a cobrar": {
        "subareas": {
            "Clientes": {
                "sumar": ["430", "431", "432", "435", "436"],
                "restar": ["437"]
            },
            "Empresas del grupo y asociadas": {
                "sumar": ["433", "434"],
                "restar": ["4933", "4934"]
            },
            "Otros deudores": {
                "sumar": ["44", "460"],
                "restar": []
            },
            "Personal y Administraciones Públicas": {
                "sumar": ["4709", "4700", "4708", "471", "472", "5580"],
                "restar": ["490", "4935"]
            }
        }
    },
    "Inversiones empresas grupo y asociadas corto plazo": {
        "subareas": {
            "Instrumentos de patrimonio": {
                "sumar": ["5303", "5304"],
                "restar": ["5393", "5394"]
            },
            "Créditos a empresas": {
                "sumar": ["5323", "5324", "5343", "5344"],
                "restar": ["5953", "5954"]
            },
            "Valores representativos de deuda": {
                "sumar": ["5313", "5314", "5333", "5334"],
                "restar": ["5943", "5944"]
            },
            "Otros activos financieros": {
                "sumar": ["5353", "5354", "5523", "5524"],
                "restar": []
            }
        }
    },
    "Inversiones financieras a corto plazo": {
        "subareas": {
            "Instrumentos de patrimonio": {
                "sumar": ["5305", "540"],
                "restar": ["5395", "549"]
            },
            "Créditos a terceros": {
                "sumar": ["5325", "5345", "542", "543", "547"],
                "restar": ["5955", "598"]
            },
            "Valores representativos de deuda": {
                "sumar": ["5315", "5335", "541", "546"],
                "restar": ["5945", "597"]
            },
            "Derivados": {
                "sumar": ["5590", "5593"],
                "restar": []
            },
            "Otros activos financieros": {
                "sumar": ["5355", "545", "548", "551", "5525", "565", "566"],
                "restar": []
            }
        }
    },
    "Periodificaciones a corto plazo": {
        "subareas": {
            "Gastos anticipados": {
                "sumar": ["480", "567"],
                "restar": []
            }
        }
    },
    "Tesorería y otros activos líquidos equivalentes": {
        "subareas": {
            "Tesorería": {
                "sumar": ["570", "571", "572", "573", "574", "575"],
                "restar": []
            },
            "Otros líquidos equivalentes": {
                "sumar": ["576"],
                "restar": []
            }
        }
    }
}
