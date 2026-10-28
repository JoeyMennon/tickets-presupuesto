# datos inventados para probar o hacer capturas
# uso: DATOS_DIR=/carpeta/vacia python manage.py demo
import uuid
from datetime import date, time, timedelta
from decimal import Decimal as D
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError

from cuentas import clasificador, lector
from cuentas.models import CERO, Evento, Mes, Previsto, Ticket

TICKETS = Path(settings.BASE_DIR) / "demo" / "tickets"

FIJOS = [(1, "Alquiler", "", "250.00", 1, True), (1, "Abono de transporte", "", "20.00", 1, True),
         (15, "Gimnasio", "", "29.90", 1, False), (12, "Música en streaming", "", "10.99", 1, False)]
OCIO = [(4, "Café con amigos", "6.00", True), (20, "Cine", "8.50", False)]
COMIDA = [  # semana, concepto, tienda, precio, cantidad
    (0, "Huevos, docena", "Súper del barrio", "2.90", 1), (0, "Leche, pack de 6", "Súper del barrio", "5.40", 1),
    (0, "Pechuga de pollo 500 g", "Carnicería", "4.20", 1), (0, "Fruta", "Frutería", "3.50", 1),
    (1, "Arroz 1 kg", "Hipermercado", "1.35", 1), (1, "Pasta 500 g", "Hipermercado", "0.95", 2),
    (1, "Garbanzos cocidos, 3 botes", "Hipermercado", "2.70", 1), (1, "Fruta", "Frutería", "3.50", 1),
    (2, "Huevos, docena", "Súper del barrio", "2.90", 1), (2, "Pechuga de pollo 500 g", "Carnicería", "4.20", 2),
    (2, "Verdura de temporada", "Frutería", "4.00", 1), (3, "Leche, pack de 6", "Súper del barrio", "5.40", 1),
    (3, "Verdura de temporada", "Frutería", "4.00", 1), (3, "Fruta", "Frutería", "3.50", 1),
]


def _mes(hoy):
    inicio = hoy.replace(day=1)
    m = Mes.objects.create(inicio=inicio, cobro=(inicio + timedelta(days=32)).replace(day=1), dinero=D("600.00"))
    dia = lambda n: inicio + timedelta(days=n - 1)
    for n, concepto, tienda, precio, cant, pagado in FIJOS:
        Previsto.objects.create(mes=m, tipo="fijo", concepto=concepto, precio=D(precio), dia=dia(n), pagado=pagado)
        if pagado:
            Ticket.objects.create(fecha=dia(n), sitio=concepto, partida="Fijo", importe=D(precio),
                                  confirmado=True, origen="banco")
    for n, concepto, precio, semanal in OCIO:
        d = dia(n)
        while d <= m.fin:
            Previsto.objects.create(mes=m, tipo="ocio", concepto=concepto, precio=D(precio), dia=d)
            if not semanal:
                break
            d += timedelta(days=7)
    semanas = m.semanas()
    for s, concepto, tienda, precio, cant in COMIDA:
        Previsto.objects.create(mes=m, tipo="comida", concepto=concepto, tienda=tienda, precio=D(precio),
                                cantidad=cant, dia=semanas[s][0])


class Command(BaseCommand):
    help = "Datos inventados: agenda y tickets leídos de demo/tickets"

    def handle(self, *args, **opciones):
        if Ticket.objects.exists() or Evento.objects.exists() or Mes.objects.exists():
            raise CommandError("La base de datos ya tiene datos. Usa DATOS_DIR con una carpeta vacía.")
        if settings.DATOS.resolve() == (Path(settings.BASE_DIR) / "datos").resolve():
            raise CommandError("Esto no va contra tus datos de verdad: pon DATOS_DIR con otra carpeta.")
        hoy = date.today()
        _mes(hoy)
        for dias, hora, titulo, color in [
            (0, time(10, 0), "Dentista", "cielo"), (1, None, "Cumple de Laura", "rosa"),
            (2, time(19, 30), "Entrenar", "salvia"), (4, time(9, 0), "Entrevista", "lavanda"),
            (-2, None, "Hacer la compra", "miel"),
        ]:
            Evento.objects.create(fecha=hoy + timedelta(days=dias), hora=hora, titulo=titulo, color=color,
                                  hecho=dias < 0)

        # el del súper se queda sin revisar para las capturas
        for nombre, partida, confirmado in [("cafe.jpg", "Cafés", True), ("fruteria.jpg", "Súper", True),
                                            ("super.jpg", "Súper", False)]:
            with open(TICKETS / nombre, "rb") as f:
                t = Ticket(fecha=hoy, origen="movil", uid=f"demo-{uuid.uuid4()}")
                t.archivo.save(nombre, File(f), save=True)
            leido = lector.leer(t.archivo.path, hoy)
            t.texto, t.importe, t.sitio = leido["texto"], leido["importe"], leido["sitio"]
            t.fecha = leido["fecha"] or hoy
            t.partida = partida
            for p in leido["productos"]:
                t.lineas.create(nombre=p["nombre"], importe=p["importe"], capricho=clasificador.es_capricho(p["nombre"]))
            t.capricho = sum((l.importe for l in t.lineas.filter(capricho=True)), CERO)
            t.confirmado = confirmado
            t.save()
            self.stdout.write(f"{nombre}: {t.sitio} {t.importe} € capricho {t.capricho} €")
