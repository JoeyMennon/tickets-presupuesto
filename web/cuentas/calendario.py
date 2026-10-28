import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from . import compra
from .models import Evento, Ticket

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
DIAS_LARGOS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
CERO = Decimal("0")


def dinero_por_dia(hoy):
    reales, previstos = defaultdict(list), defaultdict(list)
    for t in Ticket.objects.filter(confirmado=True):
        for i, (partida, importe) in enumerate(t.partes()):
            # borrar y ver ticket solo en la primera fila
            reales[t.fecha].append({"concepto": t.sitio or "Ticket", "partida": partida,
                                    "importe": importe, "ticket": t if i == 0 else None})
    for p in compra.pendientes():
        previstos[p.dia].append(p)
    return reales, previstos


def para_marcar(fecha, sitio=""):
    salida = []
    for p in compra.pendientes():
        dias = (p.dia - fecha).days
        if -13 <= dias <= 6:
            p.marcado = bool(sitio) and sitio.lower() in p.concepto.lower() and abs(dias) <= 6
            salida.append(p)
    return salida


def _celda(dia, mes, hoy, elegido, eventos, reales, previstos):
    real = sum((g["importe"] for g in reales.get(dia, [])), CERO)
    prev = sum((p.importe for p in previstos.get(dia, [])), CERO)
    return {
        "fecha": dia, "fuera": dia.month != mes, "hoy": dia == hoy, "elegido": dia == elegido,
        "finde": dia.weekday() >= 5, "eventos": eventos.get(dia, []),
        "real": real, "previsto": prev,
    }


def mes(anio, mes_n, hoy, elegido):
    semanas_fechas = calendar.Calendar().monthdatescalendar(anio, mes_n)
    ini, fin = semanas_fechas[0][0], semanas_fechas[-1][-1]
    eventos = defaultdict(list)
    for e in Evento.objects.filter(fecha__range=(ini, fin)):
        eventos[e.fecha].append(e)
    reales, previstos = dinero_por_dia(hoy)

    semanas = []
    for fechas in semanas_fechas:
        dias = [_celda(d, mes_n, hoy, elegido, eventos, reales, previstos) for d in fechas]
        semanas.append({
            "numero": fechas[0].isocalendar()[1], "dias": dias,
            "actual": fechas[0] <= hoy <= fechas[-1],
            "real": sum((d["real"] for d in dias), CERO),
            "previsto": sum((d["previsto"] for d in dias), CERO),
        })

    anterior = date(anio, mes_n, 1) - timedelta(days=1)
    siguiente = date(anio, mes_n, 28) + timedelta(days=7)
    return {
        "anio": anio, "mes_n": mes_n, "mes_nombre": MESES[mes_n - 1], "semanas": semanas,
        "anterior": f"{anterior:%Y-%m}", "siguiente": f"{siguiente:%Y-%m}",
        "meses": [{"n": i + 1, "nombre": m[:3], "clave": f"{anio}-{i + 1:02d}", "activo": i + 1 == mes_n}
                  for i, m in enumerate(MESES)],
    }


def anio(anio_n, hoy):
    eventos = set(Evento.objects.filter(fecha__year=anio_n).values_list("fecha", flat=True))
    reales, previstos = dinero_por_dia(hoy)
    meses = []
    for i in range(1, 13):
        semanas = []
        for fechas in calendar.Calendar().monthdatescalendar(anio_n, i):
            semanas.append([{
                "fecha": d, "fuera": d.month != i, "hoy": d == hoy and d.month == i,
                "evento": d in eventos, "dinero": d in reales or d in previstos,
            } for d in fechas])
        meses.append({"nombre": MESES[i - 1], "clave": f"{anio_n}-{i:02d}", "semanas": semanas,
                      "actual": anio_n == hoy.year and i == hoy.month})
    return meses


def dia(fecha, hoy, borrador=None):
    reales, previstos = dinero_por_dia(hoy)
    return {
        "borrador": borrador,
        "marcar": para_marcar(borrador.fecha if borrador else fecha, borrador.sitio if borrador else ""),
        "fecha": fecha, "nombre": DIAS_LARGOS[fecha.weekday()],
        "mes_nombre": MESES[fecha.month - 1],
        "eventos": Evento.objects.filter(fecha=fecha),
        "reales": reales.get(fecha, []), "previstos": previstos.get(fecha, []),
    }
