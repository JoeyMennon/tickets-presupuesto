# segunda opinión con un modelo de visión en Ollama, en el propio PC
# solo se usa si Tesseract tiene dudas y si Ollama está encendido
import base64
import io
import json
import os
import urllib.error
import urllib.request
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODELO = os.environ.get("OLLAMA_MODELO", "qwen2.5vl:7b")
ESPERA = int(os.environ.get("OLLAMA_ESPERA", "90"))

PROMPT = """Es la foto de un ticket de compra o una captura de un pago, en España.
Devuelve solo JSON con:
- sitio: nombre de la tienda o del comercio, corto, sin S.L. ni S.A.
- fecha: la fecha de la compra en formato AAAA-MM-DD, o vacío si no se ve
- total: el total pagado, número con punto decimal
- productos: lista de {nombre, importe} con cada producto y su importe final, ya con descuentos; vacía si es una captura sin productos
No inventes nada que no se lea."""

ESQUEMA = {
    "type": "object",
    "properties": {
        "sitio": {"type": "string"},
        "fecha": {"type": "string"},
        "total": {"type": "number"},
        "productos": {"type": "array", "items": {
            "type": "object",
            "properties": {"nombre": {"type": "string"}, "importe": {"type": "number"}},
            "required": ["nombre", "importe"],
        }},
    },
    "required": ["sitio", "fecha", "total", "productos"],
}


def disponible():
    if os.environ.get("OLLAMA_NO") == "1":
        return False
    try:
        with urllib.request.urlopen(f"{URL}/api/tags", timeout=2) as r:
            modelos = [m.get("name", "") for m in json.load(r).get("models", [])]
    except (OSError, ValueError):
        return False
    return any(m == MODELO or m.split(":")[0] == MODELO for m in modelos)


def _imagen(ruta):
    from PIL import Image, ImageOps

    if ruta.lower().endswith(".pdf"):
        return None
    im = ImageOps.exif_transpose(Image.open(ruta)).convert("RGB")
    im.thumbnail((1280, 1280 * 3))
    salida = io.BytesIO()
    im.save(salida, "JPEG", quality=88)
    return base64.b64encode(salida.getvalue()).decode()


def preguntar(ruta):
    imagen = _imagen(ruta)
    if not imagen:
        return None
    cuerpo = json.dumps({
        "model": MODELO, "stream": False, "format": ESQUEMA, "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [{"role": "user", "content": PROMPT, "images": [imagen]}],
    }).encode()
    peticion = urllib.request.Request(f"{URL}/api/chat", cuerpo, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(peticion, timeout=ESPERA) as r:
            return json.loads(json.load(r)["message"]["content"])
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        return None


def _dinero(valor):
    try:
        d = Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    return d if d > 0 else None


def completar(ruta, r, ref):
    if not disponible():
        return r
    v = preguntar(ruta)
    if not v:
        return r
    r = dict(r)
    total_v = _dinero(v.get("total"))
    prods_v = [{"nombre": str(p.get("nombre", ""))[:80], "importe": _dinero(p.get("importe"))}
               for p in v.get("productos") or []]
    prods_v = [p for p in prods_v if p["nombre"] and p["importe"]]
    suma_v = sum((p["importe"] for p in prods_v), Decimal("0")) if prods_v else None
    cuadra_v = total_v is not None and suma_v is not None and abs(total_v - suma_v) <= Decimal("0.01")
    cuadra_t = r["importe"] is not None and r["suma"] is not None and abs(r["importe"] - r["suma"]) <= Decimal("0.01")

    if r["importe"] is None or (cuadra_v and not cuadra_t):
        r["importe"] = total_v
    if prods_v and (cuadra_v or not r["productos"]) and not cuadra_t:
        r["productos"], r["suma"] = prods_v, suma_v
    if r["fecha"] is None:
        try:
            f = date.fromisoformat(v.get("fecha", ""))
            if ref - timedelta(days=400) <= f <= ref + timedelta(days=1):
                r["fecha"] = f
        except ValueError:
            pass
    if not r["conocida"] and v.get("sitio"):
        from .lector import limpiar_sitio, PISTAS_PARTIDA
        import re
        r["sitio"] = limpiar_sitio(v["sitio"])
        if r["partida"] == "Otro":
            for patron, partida in PISTAS_PARTIDA:
                if re.search(patron, r["sitio"].upper()):
                    r["partida"] = partida
                    break
    r["fuente"] = "tesseract+ollama"
    return r
