"""Decide si un producto del ticket es comida o capricho.

Primero mira lo que has corregido alguna vez y, si no, una lista de serie.
"""
import re
import unicodedata

# Palabras de capricho. Se buscan como palabra entera o como principio de palabra.
CAPRICHOS = [
    # dulces
    r"CHOCOLAT", r"CHOCO\.?\s*(NEGRO|LECHE|BLANCO|AVELL|NEGR|CRUJ)", r"BOMBON", r"TRUFA",
    r"NOCILLA", r"NUTELLA", r"KINDER", r"OREO", r"CHIPS AHOY", r"PRINCIPE", r"FILIPINOS",
    r"GALLETA", r"GLLTA", r"BOLLO", r"BOLLERIA", r"DONUT", r"DONETES", r"CROISSANT", r"CRUASAN",
    r"NAPOLITANA", r"MAGDALENA", r"MUFFIN", r"BROWNIE", r"PASTEL", r"TARTA", r"BIZCOCHO",
    r"PALMERA", r"CHURRO", r"GOFRE", r"CREPE", r"NATILLAS", r"FLAN", r"MOUSSE", r"COOKIE",
    r"GOMINOLA", r"GOMIS", r"CHUCHE", r"CARAMELO", r"REGALIZ", r"CHICLE", r"PIRULETA", r"LACASITO",
    r"M&M", r"MARS", r"SNICKERS", r"TWIX", r"KIT ?KAT", r"MILKA", r"TOBLERONE", r"TURRON", r"MAZAPAN",
    r"HELADO", r"MAGNUM", r"CORNETTO", r"POLO",
    # salados de picar
    r"PATATAS? FRITAS?", r"PAT\.? ?FRIT", r"CHIPS", r"SNACK", r"NACHOS", r"DORITOS", r"PRINGLES",
    r"RUFFLES", r"LAYS", r"CHEETOS", r"PALOMITAS", r"GUSANITOS", r"BOCABITS", r"TORTILLA CHIPS",
    # bebidas
    r"REFRESCO", r"COCA[ -]?COLA", r"PEPSI", r"FANTA", r"SPRITE", r"7 ?UP", r"SCHWEPPES",
    r"AQUARIUS", r"NESTEA", r"MONSTER", r"RED ?BULL", r"BURN", r"ENERG", r"BATIDO",
    r"CERVEZA", r"CERV\.", r"ESTRELLA GALICIA", r"MAHOU", r"VINO", r"SIDRA", r"VERMUT",
    r"TINTO DE VERANO", r"GINEBRA", r"RON", r"WHISKY", r"VODKA", r"LICOR", r"CAVA", r"SANGRIA",
    # comida preparada de capricho
    r"PIZZA", r"HAMBURGUESA PREPARADA", r"KEBAB",
]
_PATRON = re.compile(r"\b(" + "|".join(CAPRICHOS) + r")")


def normalizar(nombre):
    """Mayúsculas, sin tildes ni cantidades, para que el mismo producto dé la misma clave."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", nombre) if unicodedata.category(c) != "Mn")
    limpio = re.sub(r"[^A-Z& ]", " ", sin_tildes.upper())
    palabras = [p for p in limpio.split() if len(p) > 1 or p == "&"]
    return " ".join(palabras)[:80]


def de_serie(nombre):
    return bool(_PATRON.search(normalizar(nombre)))


def es_capricho(nombre):
    from .models import Producto
    clave = normalizar(nombre)
    aprendido = Producto.objects.filter(clave=clave).values_list("capricho", flat=True).first()
    if aprendido is not None:
        return aprendido
    return de_serie(nombre)


def aprender(nombre, capricho):
    """Guarda la corrección solo si cambia lo que haría de serie o lo que ya sabía."""
    from .models import Producto
    clave = normalizar(nombre)
    if not clave:
        return
    if capricho == de_serie(nombre):
        Producto.objects.filter(clave=clave).delete()
    else:
        Producto.objects.update_or_create(clave=clave, defaults={"capricho": capricho})
