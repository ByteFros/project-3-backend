from ..models.areaContable import SubAreaContable

def encontrar_subarea_por_cuenta(codigo_cuenta):
    try:
        cuenta_num = int(str(codigo_cuenta).split('.')[0])
    except:
        return None

    for subarea in SubAreaContable.objects.all():
        if cuenta_num in subarea.codigos_pos_list() or cuenta_num in subarea.codigos_neg_list():
            return subarea
    return None



def buscar_subarea_por_cuenta(cuenta_str):
    """
    Busca la subárea contable a la que pertenece una cuenta.
    Elimina espacios, trata strings mal formateados y busca en positivos y negativos.
    """
    if not cuenta_str:
        return None

    cuenta_limpia = cuenta_str.strip().split(".")[0]

    subareas = SubAreaContable.objects.all()
    for sub in subareas:
        codigos_pos = [
            c.strip() for c in (sub.codigos_positivos or "").split(",") if c.strip()
        ]
        codigos_neg = [
            c.strip() for c in (sub.codigos_negativos or "").split(",") if c.strip()
        ]

        if cuenta_limpia in codigos_pos or cuenta_limpia in codigos_neg:
            return sub

    return None
