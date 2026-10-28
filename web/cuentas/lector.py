"""Saca total, tienda y fecha de la foto o el PDF de un ticket."""
import re
import subprocess
from datetime import date
from decimal import Decimal

TIENDAS = {
    "MERCADONA": ("Mercadona", "Súper"),
    "ALCAMPO": ("Alcampo", "Súper"),
    "FROIZ": ("Froiz", "Súper"),
    "GADIS": ("Gadis", "Súper"),
    "LIDL": ("Lidl", "Súper"),
    "CARREFOUR": ("Carrefour", "Súper"),
    "EROSKI": ("Eroski", "Súper"),
    "MCDONALD": ("McDonald's", "Comida fuera"),
    "KFC": ("KFC", "Comida fuera"),
    "BURGER KING": ("Burger King", "Comida fuera"),
}

IMPORTE = re.compile(r"(\d{1,4}[.,]\d{2})(?!\d)")
FECHA = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b")
# Capturas de pagos del móvil: "6,00 €" y "28 oct" o "28 de octubre de 2026"
EUROS = re.compile(r"(\d{1,4}[.,]\d{2})\s*€")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
FECHA_TEXTO = re.compile(r"\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(MESES) + r")[a-z]*\.?(?:\s+(?:de\s+)?(\d{4}))?", re.I)
# Líneas de la captura que nunca son el nombre del comercio
NO_ES_SITIO = re.compile(r"€|\d{1,2}:\d{2}|débito|crédito|tarjeta|obtén|activar", re.I)


def _idiomas():
    """Español si está instalado: lee mejor tildes y eñes."""
    try:
        hay = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return "eng"
    return "spa+eng" if "spa" in hay else "eng"


def texto(ruta):
    if ruta.lower().endswith(".pdf"):
        orden = ["pdftotext", "-layout", ruta, "-"]
    else:
        orden = ["tesseract", ruta, "stdout", "--psm", "4", "-l", _idiomas()]
    try:
        return subprocess.run(orden, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _decimal(cadena):
    return Decimal(cadena.replace(",", "."))


def total(lineas):
    """El importe de la última línea con TOTAL que no sea subtotal ni de impuestos."""
    candidatos = []
    for i, linea in enumerate(lineas):
        mayus = linea.upper()
        if "TOTAL" not in mayus or "SUBTOTAL" in mayus or "IVA" in mayus or "BASE" in mayus:
            continue
        importes = IMPORTE.findall(linea)
        if not importes and i + 1 < len(lineas):
            importes = IMPORTE.findall(lineas[i + 1])
        if importes:
            candidatos.append(_decimal(importes[-1]))
    if candidatos:
        return max(candidatos)
    return None


# Líneas de producto: lo que no es nombre de producto
PRECIO_FINAL = re.compile(r"(-?\d{1,4}[.,]\d{2})\s*(?:€|EUR|[A-Z])?\s*$", re.I)
NO_ES_PRODUCTO = re.compile(
    r"TOTAL|IVA|I\.V\.A|BASE|CUOTA|TARJETA|EFECTIVO|CAMBIO|ENTREGAD|IMPORTE|VISA|MASTERCARD|"
    r"PAGO|N\.?I\.?F|C\.?I\.?F|TEL[EÉ]F|FACTURA|DEVOLUCI|AHORRO|PUNTOS|SALDO|CONTACTLESS|AUTORIZ", re.I)
DESCUENTO = re.compile(r"DTO|DESC|PROMO|OFERTA|REBAJA", re.I)


def _nombre(trozo):
    """Quita cantidades, pesos y precios por kilo; deja solo el nombre."""
    trozo = re.sub(r"\b\d+\s*[xX]\s*\d*[.,]?\d*\s*(kg|g|gr|l|ml|cl)?\b|\d+\s*%", " ", trozo, flags=re.I)
    trozo = re.sub(r"\d+[.,]?\d*\s*(kg|g|gr|l|ml|cl|ud|uds|u)?\b", " ", trozo, flags=re.I)
    trozo = re.sub(r"€\s*/\s*kg|/kg|€|\bx\b", " ", trozo, flags=re.I)
    return " ".join(trozo.split()).strip(" .,:-*")


def productos(lineas):
    """Cada producto con su importe. Los de peso traen el nombre en una línea y el precio en la siguiente."""
    salida, suelto = [], None
    for linea in lineas:
        if re.search(r"\bTOTAL\b", linea, re.I) and not re.search(r"SUBTOTAL", linea, re.I):
            break
        m = PRECIO_FINAL.search(linea)
        nombre = _nombre(linea[:m.start()] if m else linea)
        if NO_ES_PRODUCTO.search(linea):
            suelto = None
            continue
        if not m:
            suelto = nombre if len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", nombre)) >= 3 else None
            continue
        importe = _decimal(m.group(1))
        letras = len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", nombre))
        if (importe < 0 or DESCUENTO.search(linea)) and salida:
            salida[-1]["importe"] -= abs(importe)
        elif letras >= 3:
            salida.append({"nombre": nombre[:80], "importe": importe})
        elif suelto:
            salida.append({"nombre": suelto[:80], "importe": importe})
        suelto = None
    return [p for p in salida if p["importe"] > 0]


def _fecha_texto(crudo, ref):
    """Fecha escrita con el mes en letra; sin año, el de la fecha de referencia."""
    for d, mes, a in FECHA_TEXTO.findall(crudo):
        anio = int(a) if a else ref.year
        try:
            f = date(anio, MESES.index(mes.lower()[:3]) + 1, int(d))
        except ValueError:
            continue
        if not a and f > ref:
            f = f.replace(year=anio - 1)
        return f
    return None


def _sitio_generico(lineas):
    """Nombre del comercio en las capturas de Google Wallet y parecidas."""
    for i, linea in enumerate(lineas):
        if linea.lower().startswith("nombre del extracto") and i + 1 < len(lineas):
            return lineas[i + 1]
    for linea in lineas[:3]:
        if len(linea) >= 3 and re.search(r"[A-Za-z]{3}", linea) and not NO_ES_SITIO.search(linea):
            return linea
    return ""


def leer(ruta, ref=None):
    ref = ref or date.today()
    crudo = texto(ruta)
    lineas = [l.strip() for l in crudo.splitlines() if l.strip()]
    mayus = crudo.upper()
    sitio, partida = "", "Otro"
    for clave, (nombre, tipo) in TIENDAS.items():
        if clave in mayus:
            sitio, partida = nombre, tipo
            break
    if not sitio:
        sitio = _sitio_generico(lineas).title()[:60]
    fecha = None
    for d, m, a in FECHA.findall(crudo):
        a = int(a) + (2000 if len(a) == 2 else 0)
        try:
            fecha = date(a, int(m), int(d))
            break
        except ValueError:
            continue
    fecha = fecha or _fecha_texto(crudo, ref)
    importe = total(lineas)
    if importe is None:
        euros = EUROS.findall(crudo)
        importe = _decimal(euros[0]) if euros else None
    return {"texto": crudo, "importe": importe, "productos": productos(lineas), "sitio": sitio, "partida": partida, "fecha": fecha}
