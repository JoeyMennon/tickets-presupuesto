"""Cuentas del mes: lo cobrado, lo gastado según los tickets y lo previsto que falta por pagar."""
from .models import CERO, Mes, Previsto, Ticket

def tickets_del_mes(mes):
    return Ticket.objects.filter(confirmado=True, fecha__gte=mes.inicio, fecha__lt=mes.cobro)


def cubiertos():
    return {c for t in Ticket.objects.filter(confirmado=True).exclude(cubre="") for c in t.claves()}


def pendientes(mes=None):
    """Lo previsto que ni está pagado ni lo cubre ningún ticket."""
    mes = mes or Mes.actual()
    if mes is None:
        return []
    hechos = cubiertos()
    return [p for p in mes.previstos.filter(pagado=False) if p.clave not in hechos]


def semana_de(mes, fecha):
    for ini, fin in mes.semanas():
        if ini <= fecha <= fin:
            return ini, fin
    return mes.semanas()[-1]


def resumen(mes):
    if mes is None:
        return {"dinero": CERO, "gastado": CERO, "queda": CERO, "pendiente": CERO, "libre": CERO,
                "caprichos": CERO, "inicio": None, "fin": None, "sin_mes": True}
    partes = [(t, partida, importe) for t in tickets_del_mes(mes) for partida, importe in t.partes()]
    gastado = sum((i for _, _, i in partes), CERO)
    caprichos = sum((i for _, p, i in partes if p == "Caprichos"), CERO)
    por_pagar = sum((p.importe for p in pendientes(mes)), CERO)
    queda = mes.dinero - gastado
    return {"dinero": mes.dinero, "gastado": gastado, "queda": queda, "pendiente": por_pagar,
            "libre": queda - por_pagar, "caprichos": caprichos, "inicio": mes.inicio, "fin": mes.fin,
            "partes": partes, "por_partida": _por_partida(partes)}


def _por_partida(partes):
    """Lo gastado sumado por partida, de más a menos."""
    sumas = {}
    for _, partida, importe in partes:
        sumas[partida] = sumas.get(partida, CERO) + importe
    return sorted(sumas.items(), key=lambda x: -x[1])
