# genera demo/tickets, hace falta pillow
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent / "tickets"
FUENTE = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"
NEGRITA = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Bold.ttf"
ANCHO = 26

TICKETS = {
    "super.jpg": ("SUPERMERCADO EJEMPLO", "C/ Inventada 12", [
        ("LECHE SEMI 6X1L", "5,40"), ("HUEVOS DOCENA", "2,90"),
        ("PECHUGA POLLO", "4,20"), ("TOMATE RAMA", "1,85"),
        ("CHOCOLATE NEGRO", "1,95"), ("PATATAS FRITAS", "1,49"),
        ("PLATANO", "2,10"),
    ]),
    "cafe.jpg": ("CAFETERIA LA PLAZA", "Plaza Mayor 3", [
        ("CAFE CON LECHE", "1,60"), ("TOSTADA TOMATE", "2,20"),
    ]),
    "fruteria.jpg": ("FRUTERIA EL HUERTO", "Mercado, puesto 8", [
        ("MANZANA GOLDEN", "2,35"), ("NARANJA ZUMO", "1,90"), ("CALABACIN", "0,95"),
    ]),
}


def linea(izq, der=""):
    return izq[: ANCHO - len(der) - 1].ljust(ANCHO - len(der)) + der


def hacer(nombre, tienda, calle, productos, dia):
    total = sum(float(p.replace(",", ".")) for _, p in productos)
    filas = [("b", tienda.center(ANCHO)), ("", calle.center(ANCHO)), ("", "CIF B00000000".center(ANCHO)), ("", ""),
             ("", linea(f"{dia:%d/%m/%Y} 11:42", "N 42")), ("", "-" * ANCHO)]
    filas += [("", linea(n, p)) for n, p in productos]
    filas += [("", "-" * ANCHO), ("b", linea("TOTAL", f"{total:.2f}".replace(".", ",") + " EUR")),
              ("", linea("TARJETA", f"{total:.2f}".replace(".", ","))), ("", ""), ("", "GRACIAS POR SU VISITA".center(ANCHO))]
    f, fb = ImageFont.truetype(FUENTE, 32), ImageFont.truetype(NEGRITA, 32)
    alto = 60 + 44 * len(filas)
    papel = Image.new("RGB", (40 + 20 * ANCHO + 40, alto), "#fbf8f1")
    d = ImageDraw.Draw(papel)
    for i, (estilo, texto) in enumerate(filas):
        d.text((40, 30 + 44 * i), texto, font=fb if estilo else f, fill="#2b2b2b")
    fondo = Image.new("RGB", (papel.width + 80, papel.height + 80), "#e4dccf")
    sombra = Image.new("RGB", papel.size, "#cfc5b6")
    fondo.paste(sombra, (46, 48))
    fondo.paste(papel, (40, 40))
    fondo.save(AQUI / nombre, quality=88)


if __name__ == "__main__":
    AQUI.mkdir(exist_ok=True)
    hoy = date.today()
    for i, (nombre, datos) in enumerate(TICKETS.items()):
        hacer(nombre, *datos, hoy - timedelta(days=i))
    print("Hechos:", ", ".join(TICKETS))
