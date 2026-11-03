import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

from . import vision

TIENDAS = {
    "MERCADONA": ("Mercadona", "Súper"),
    "ALCAMPO": ("Alcampo", "Súper"),
    "FROIZ": ("Froiz", "Súper"),
    "GADIS": ("Gadis", "Súper"),
    "LIDL": ("Lidl", "Súper"),
    "CARREFOUR": ("Carrefour", "Súper"),
    "EROSKI": ("Eroski", "Súper"),
    "DIA %": ("Dia", "Súper"),
    "SUPERMERCADOS DIA": ("Dia", "Súper"),
    "VEGO": ("Vego", "Súper"),
    "FAMILIA": ("Familia", "Súper"),
    "MCDONALD": ("McDonald's", "Comida fuera"),
    "KFC": ("KFC", "Comida fuera"),
    "BURGER KING": ("Burger King", "Comida fuera"),
    "TELEPIZZA": ("Telepizza", "Comida fuera"),
}
# si no es una tienda conocida, pistas por el nombre
PISTAS_PARTIDA = [
    (r"COFFEE|CAF[EÉ]|CAFETER", "Cafés"),
    (r"PANADER|PANIFIC|HORNO|OBRADOIRO", "Pan"),
    (r"BURGER|PIZZ|RESTAURA|KEBAB|SUSHI|TABERNA|MES[OÓ]N|BAR\b", "Comida fuera"),
    (r"CINE|TEATRO|ENTRADAS|STEAM|PLAYSTATION|NINTENDO", "Ocio"),
    (r"SUPERMERCADO|HIPERMERCADO|FRUTER|CARNICER|PESCADER|ALIMENTACI", "Súper"),
    (r"PASTELER|CONFITER|HELADER|GOLOSINA|CHUCHE", "Caprichos"),
]

# importes: 12,40  1.93  ,95 (sin el cero)  1, 93 (con espacio tras la coma)
IMPORTE = re.compile(r"(?<![\d.,])(\d{0,4})[.,] ?(\d{2})(?![\d%])")
EUROS = re.compile(r"(?<![\d.,])(\d{0,4})[.,] ?(\d{2})\s*(?:€|EUR)", re.I)
# a veces se come la coma: "210 €" es 2,10
EUROS_SIN_COMA = re.compile(r"(?<![\d.,])(\d{3,5})\s*[€¢]")
FECHA = re.compile(r"(?<!\d)(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})(?!\d)")
FECHA_ESPACIOS = re.compile(r"(?<!\d)(\d{1,2}) (\d{1,2}) (20\d{2})(?!\d)")
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
FECHA_TEXTO = re.compile(r"\b(\d{1,2})\s+(?:de\s+)?(" + "|".join(MESES) + r")[a-z]*\.?(?:\s+(?:de\s+)?(\d{4}))?", re.I)
CIF = re.compile(r"\b(?:C\.?I\.?F|N\.?I\.?F)\.?\s*:?\s*([A-Z]?\d{7,8}[A-Z0-9]?)\b", re.I)

LINEA_TOTAL = re.compile(r"\bTOTAL\b|\bTOT\b|A PAGAR|\bIMPORTE\b", re.I)
NO_ES_TOTAL = re.compile(r"SUBTOTAL|\bIVA\b|BASE|\bART|VENDIDOS|PUNTOS|SALDO|AHORRO|DESCUENTO", re.I)
NO_ES_SITIO = re.compile(
    r"€|\d{1,2}:\d{2}|débito|crédito|tarjeta|obtén|activar|datos de la|factura|simplificada|"
    r"ticket|tique|recibo|bienvenid|gracias|operaci[oó]n|^www\.|\.com\b", re.I)
ETIQUETA_SITIO = re.compile(r"^(?:(?:comercio|establecimiento|beneficiario)\s*:|nombre del extracto\s*:?)\s*(.*)$", re.I)
# lo que el OCR lee torcido: TRRJETH es TARJETA
PALABRAS_PAGO = ["TARJETA", "TOTAL", "CAMBIO", "EFECTIVO", "ENTREGA", "CONTADO", "DEVOLVER", "IMPORTE"]


def _parecida(palabra, lista, minimo=.75):
    from difflib import SequenceMatcher
    palabra = palabra.upper()
    return any(SequenceMatcher(None, palabra, p).ratio() >= minimo for p in lista)


def _a_decimal(enteros, centimos):
    return Decimal(f"{enteros or '0'}.{centimos}")


def importes(linea):
    return [_a_decimal(e, c) for e, c in IMPORTE.findall(linea)]


# --- de la foto al texto ---

def _variantes(ruta, carpeta):
    # dos versiones de la foto: gris con contraste y blanco y negro sin sombras
    import numpy as np
    from PIL import Image, ImageFilter, ImageOps

    im = ImageOps.exif_transpose(Image.open(ruta)).convert("L")
    if np.asarray(im).mean() < 110:
        im = ImageOps.invert(im)
    if im.width < 1600:
        f = min(1600 / im.width, 3)
        im = im.resize((int(im.width * f), int(im.height * f)), Image.LANCZOS)
    gris = ImageOps.autocontrast(im, cutoff=1)
    a = np.asarray(im).astype(np.float32)
    fondo = np.asarray(im.filter(ImageFilter.GaussianBlur(max(im.width // 40, 15)))).astype(np.float32)
    sin_sombras = Image.fromarray(np.clip(a / (fondo + 1) * 235, 0, 255).astype(np.uint8))
    bn = sin_sombras.point(lambda v: 255 if v > 170 else 0)
    rutas = []
    for nombre, imagen in (("gris", gris), ("bn", bn)):
        destino = os.path.join(carpeta, f"{nombre}.png")
        imagen.save(destino)
        rutas.append(destino)
    return rutas


def _idiomas():
    try:
        hay = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10).stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        return "eng"
    return "spa+eng" if "spa" in hay else "eng"


def _ocr(ruta, idiomas):
    try:
        orden = ["tesseract", ruta, "stdout", "--psm", "4", "-l", idiomas]
        return subprocess.run(orden, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _pdf_a_imagen(ruta, carpeta):
    base = os.path.join(carpeta, "pagina")
    try:
        subprocess.run(["pdftoppm", "-r", "300", "-png", "-f", "1", "-l", "1", ruta, base], timeout=60, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    hechas = sorted(f for f in os.listdir(carpeta) if f.startswith("pagina"))
    return os.path.join(carpeta, hechas[0]) if hechas else None


def textos(ruta):
    with tempfile.TemporaryDirectory() as carpeta:
        if ruta.lower().endswith(".pdf"):
            try:
                hecho = subprocess.run(["pdftotext", "-layout", ruta, "-"], capture_output=True, text=True, timeout=60).stdout
            except (OSError, subprocess.TimeoutExpired):
                hecho = ""
            if len(re.findall(r"[A-Za-z]", hecho)) > 20:
                return [hecho]
            # pdf escaneado: se pasa a imagen y se lee como una foto
            ruta = _pdf_a_imagen(ruta, carpeta)
            if not ruta:
                return [hecho]
        try:
            rutas = _variantes(ruta, carpeta)
        except Exception:
            rutas = [ruta]
        idiomas = _idiomas()
        with ThreadPoolExecutor(max_workers=len(rutas)) as hilos:
            return list(hilos.map(lambda r: _ocr(r, idiomas), rutas))


def texto(ruta):
    return textos(ruta)[0]


# --- del texto a los datos ---

def total(lineas, suma_productos=None):
    candidatos = []
    for i, linea in enumerate(lineas):
        if not LINEA_TOTAL.search(linea) or NO_ES_TOTAL.search(linea):
            continue
        hay = importes(linea)
        if not hay and i + 1 < len(lineas):
            hay = importes(lineas[i + 1])
        candidatos += [h for h in hay[-1:] if h > 0]
    if suma_productos and any(abs(c - suma_productos) <= Decimal("0.01") for c in candidatos):
        return suma_productos
    if candidatos:
        return max(candidatos)
    return None


def _total_suelto(crudo):
    # capturas del banco y del móvil: el importe grande con el €
    con_coma = [_a_decimal(e, c) for e, c in EUROS.findall(crudo)]
    if con_coma:
        return con_coma[0]
    sin_coma = EUROS_SIN_COMA.findall(crudo)
    if sin_coma:
        n = sin_coma[0]
        return Decimal(f"{n[:-2]}.{n[-2:]}")
    return None


PRECIO_FINAL = re.compile(r"(-?)(\d{0,4})[.,] ?(\d{2})(?:\s*(?:€|EUR\.?|[A-Z]))*\s*$", re.I)
NO_ES_PRODUCTO = re.compile(
    r"TOTAL|\bTOT\b|IVA|I\.V\.A|BASE|CUOTA|TARJETA|EFECTIVO|CAMBIO|ENTREGAD|ENTREGA|CONTADO|DEVOLVER|IMPORTE|VISA|"
    r"MASTERCARD|PAGO|N\.?I\.?F|C\.?I\.?F|TEL[EÉ]F|FACTURA|DEVOLUCI|AHORRO|PUNTOS|SALDO|CONTACTLESS|AUTORIZ|"
    r"SECUENCIA|FECHA|HORA|\d{1,2}:\d{2}", re.I)
SECCION = re.compile(r"^(ALIMENTACI|BODEGA|BEBIDAS|DROGUER|PERFUMER|FRESCOS|CONGELAD|LIMPIEZA|DESCRIPCI)", re.I)
DESCUENTO = re.compile(r"DTO|DESC|PROMO|OFERTA|REBAJA", re.I)
FIN_PRODUCTOS = re.compile(r"\bTOTAL\b|\bTOT\b|\*\s*TOTAL", re.I)


def _nombre(trozo):
    trozo = re.sub(r"\b\d+\s*[xX×%]\s*\d*[.,]?\d*\s*(kg|g|gr|l|ml|cl)?\b|\d+\s*%", " ", trozo, flags=re.I)
    trozo = re.sub(r"\d+[.,]?\d*\s*(kg|g|gr|l|ml|cl|ud|uds|u)?\b", " ", trozo, flags=re.I)
    trozo = re.sub(r"€\s*/\s*kg|/kg|€|\bx\b|×|=", " ", trozo, flags=re.I)
    return " ".join(trozo.split()).strip(" .,:;-*|%]“”\"'")


def _letras(texto):
    return len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", texto))


def productos(lineas):
    # casos: nombre y precio en la misma línea; nombre en una y precio en la siguiente;
    # y en algunos súper, todos los precios arriba y los nombres debajo
    salida, suelto, nombres_solos, precios_solos = [], None, [], []
    for linea in lineas:
        if FIN_PRODUCTOS.search(linea) and not re.search(r"SUBTOTAL", linea, re.I):
            break
        palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{5,}", linea)
        if (NO_ES_PRODUCTO.search(linea) or SECCION.search(linea) or re.match(r"^\W*[€¢£]", linea)
                or re.search(r"[A-Za-z]\s*:\s*\W*\d", linea) or any(_parecida(p, PALABRAS_PAGO) for p in palabras)):
            suelto = None
            continue
        m = PRECIO_FINAL.search(linea)
        nombre = _nombre(linea[:m.start()] if m else linea)
        if not m:
            if _letras(nombre) >= 3:
                suelto = nombre
                nombres_solos.append(nombre)
            continue
        importe = _a_decimal(m.group(2), m.group(3))
        negativo = m.group(1) == "-"
        if (negativo or DESCUENTO.search(linea)) and salida:
            salida[-1]["importe"] -= importe
        elif _letras(nombre) >= 3:
            salida.append({"nombre": nombre[:80], "importe": importe})
        elif suelto:
            salida.append({"nombre": suelto[:80], "importe": importe})
            nombres_solos.remove(suelto)
        else:
            precios_solos.append(importe)
        suelto = None
    # precios sin nombre y nombres sin precio, emparejados por orden
    if precios_solos and len(precios_solos) == len(nombres_solos):
        salida += [{"nombre": n[:80], "importe": p} for n, p in zip(nombres_solos, precios_solos)]
    return [p for p in salida if p["importe"] > 0]


def _fechas(crudo, lineas, ref):
    candidatas = []
    for i, linea in enumerate(lineas):
        pesa = 2 if re.search(r"FECHA", linea, re.I) else 1
        for d, m, a in FECHA.findall(linea) + FECHA_ESPACIOS.findall(linea):
            a = int(a) + (2000 if len(a) == 2 else 0)
            try:
                candidatas.append((pesa, date(a, int(m), int(d))))
            except ValueError:
                continue
        for d, mes, a in FECHA_TEXTO.findall(linea):
            anio = int(a) if a else ref.year
            try:
                f = date(anio, MESES.index(mes.lower()[:3]) + 1, int(d))
            except ValueError:
                continue
            if not a and f > ref:
                f = f.replace(year=anio - 1)
            candidatas.append((pesa, f))
    validas = [(p, f) for p, f in candidatas if ref - timedelta(days=400) <= f <= ref + timedelta(days=1)]
    if not validas:
        return None
    return max(validas, key=lambda x: x[0])[1]


def limpiar_sitio(nombre):
    nombre = re.sub(r"\((?:ESPA[ÑN]A|SPAIN|ES)\)|\bS\.?L\.?U?\b\.?|\bS\.?A\.?U?\b\.?", " ", nombre, flags=re.I)
    nombre = re.sub(r"[^\wÁÉÍÓÚÑáéíóúñ'&. -]", " ", nombre)
    nombre = " ".join(nombre.split()).strip(" .-")
    return nombre.title()[:60] if nombre.isupper() or nombre.islower() else nombre[:60]


def _sitio_generico(lineas):
    for i, linea in enumerate(lineas):
        m = ETIQUETA_SITIO.match(linea)
        if m:
            resto = m.group(1).strip() or (lineas[i + 1] if i + 1 < len(lineas) else "")
            if _letras(resto) >= 3:
                return resto
    for linea in lineas[:6]:
        letras = _letras(linea)
        if letras >= 4 and letras / max(len(linea.replace(" ", "")), 1) > .7 and not NO_ES_SITIO.search(linea):
            return linea
    return ""


def clave_nombre(texto):
    from .clasificador import normalizar
    return "n:" + normalizar(texto)[:40] if texto else ""


def claves_tienda(crudo):
    # para aprender: el CIF y cómo sale el nombre en el ticket
    claves = []
    cif = CIF.search(crudo)
    if cif:
        claves.append("cif:" + cif.group(1).upper())
    lineas = [l.strip() for l in crudo.splitlines() if l.strip()]
    nombre = clave_nombre(_sitio_generico(lineas))
    if nombre and len(nombre) > 4:
        claves.append(nombre)
    return claves


def _tienda_aprendida(crudo):
    try:
        from .models import Tienda
        claves = claves_tienda(crudo)
        for clave in claves:
            t = Tienda.objects.filter(clave=clave).first()
            if t:
                return t.nombre, t.partida
    except Exception:
        pass
    return None


def tienda_y_partida(crudo, lineas):
    aprendida = _tienda_aprendida(crudo)
    if aprendida:
        return aprendida[0], aprendida[1], True
    mayus = crudo.upper()
    for clave, (nombre, tipo) in TIENDAS.items():
        if clave in mayus:
            return nombre, tipo, True
    palabras = set(re.findall(r"[A-ZÁÉÍÓÚÑ]{5,}", mayus))
    for clave, (nombre, tipo) in TIENDAS.items():
        if " " not in clave and len(clave) >= 5 and any(_parecida(p, [clave], .8) for p in palabras):
            return nombre, tipo, True
    sitio = limpiar_sitio(_sitio_generico(lineas))
    for patron, partida in PISTAS_PARTIDA:
        if re.search(patron, mayus):
            return sitio, partida, False
    return sitio, "Otro", False


def analizar(crudo, ref):
    lineas = [l.strip() for l in crudo.splitlines() if l.strip()]
    prods = productos(lineas)
    suma = sum((p["importe"] for p in prods), Decimal("0")) if prods else None
    importe = total(lineas, suma)
    seguro = importe is not None
    if importe is None and len(prods) >= 2 and any(abs(v - suma) <= Decimal("0.01") for v in importes(crudo)):
        importe, seguro = suma, True
    if importe is None:
        importe = _total_suelto(crudo)
    sitio, partida, conocida = tienda_y_partida(crudo, lineas)
    # en las capturas el nombre del comercio con su importe no es un producto
    prods = [p for p in prods if clave_nombre(p["nombre"]) != clave_nombre(sitio)]
    suma = sum((p["importe"] for p in prods), Decimal("0")) if prods else None
    return {"texto": crudo, "importe": importe, "seguro": seguro, "productos": prods, "suma": suma, "sitio": sitio,
            "partida": partida, "conocida": conocida, "fecha": _fechas(crudo, lineas, ref)}


def _cuadra(r):
    return r["importe"] is not None and r["suma"] is not None and abs(r["importe"] - r["suma"]) <= Decimal("0.01")


def _puntos(r):
    return ((4 if r["seguro"] else 1 if r["importe"] is not None else 0) + (3 if _cuadra(r) else 0) + (2 if r["fecha"] else 0)
            + (2 if r["conocida"] else 1 if r["sitio"] else 0) + min(len(r["productos"]), 4) * .5)


def _juntar(lecturas):
    # la mejor lectura y lo que le falte, de las otras
    lecturas = sorted(lecturas, key=_puntos, reverse=True)
    mejor = dict(lecturas[0])
    for otra in lecturas[1:]:
        for campo in ("importe", "fecha"):
            if mejor[campo] is None and otra[campo] is not None:
                mejor[campo] = otra[campo]
        if not mejor["conocida"] and otra["conocida"]:
            mejor.update(sitio=otra["sitio"], partida=otra["partida"], conocida=True)
        if not mejor["sitio"] and otra["sitio"]:
            mejor["sitio"] = otra["sitio"]
    mejor["texto"] = "\n\n---\n\n".join(l["texto"] for l in lecturas)
    return mejor


def _dudas(r):
    dudas = []
    if r["importe"] is None:
        dudas.append("No he encontrado el total.")
    elif r["productos"] and not _cuadra(r):
        suma, tot = (f"{v:.2f}".replace(".", ",") for v in (r["suma"], r["importe"]))
        dudas.append(f"Los productos suman {suma} € y el total es {tot} €: revisa alguno.")
    if r["fecha"] is None:
        dudas.append("No he visto la fecha.")
    if not r["sitio"]:
        dudas.append("No sé de qué sitio es.")
    return dudas


def leer(ruta, ref=None):
    ref = ref or date.today()
    r = _juntar([analizar(t, ref) for t in textos(ruta) if t.strip()] or [analizar("", ref)])
    r["fuente"] = "tesseract"
    if _dudas(r) or not r["conocida"]:
        r = vision.completar(ruta, r, ref)
    r["dudas"] = " ".join(_dudas(r))
    return r
