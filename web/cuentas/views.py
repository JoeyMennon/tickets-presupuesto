import hashlib
import socket
import ssl
import uuid
from datetime import date, timedelta
from urllib.parse import quote, urlencode
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.conf import settings
import segno
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import clasificador, calendario as cal
from . import compra as plan_compra
from . import lector
from .models import CERO, Evento, Mes, Movil, Previsto, Ticket

def _importe(texto):
    # vale '3,91', '3.91' o '3,91 €'
    try:
        valor = Decimal((texto or "").replace("€", "").replace(" ", "").replace(",", "."))
    except InvalidOperation:
        return None
    return valor.quantize(Decimal("0.01")) if valor > 0 else None


def _fecha(texto):
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        return None


# --- plan del mes ---

def _mes_elegido(request):
    pk = request.GET.get("id") or request.POST.get("mes")
    return Mes.objects.filter(pk=pk).first() if pk else Mes.actual()


def _volver_mes(m):
    return redirect(f"/mes/?id={m.pk}") if m else redirect("mes")


def mes(request):
    m = _mes_elegido(request)
    if request.method == "POST" and m:
        dinero = _importe(request.POST.get("dinero"))
        inicio = _fecha(request.POST.get("inicio")) or m.inicio
        cobro = _fecha(request.POST.get("cobro")) or m.cobro
        if dinero is None or cobro <= inicio:
            messages.error(request, "Revisa el dinero y que el cobro sea después del inicio.")
        else:
            m.dinero, m.inicio, m.cobro = dinero, inicio, cobro
            m.save()
            messages.success(request, "Mes guardado.")
        return _volver_mes(m)

    grupos = []
    if m:
        hechos = plan_compra.cubiertos()
        for tipo, nombre in Previsto.TIPOS:
            lista = list(m.previstos.filter(tipo=tipo))
            for p in lista:
                p.cubierto = p.pagado or p.clave in hechos
            grupos.append({"tipo": tipo, "nombre": nombre, "lista": lista,
                           "total": sum((p.importe for p in lista), CERO)})
    siguiente_inicio = m.cobro if m else date.today()
    return render(request, "cuentas/mes.html", {
        "m": m, "meses": Mes.objects.all(), "grupos": grupos,
        "resumen": plan_compra.resumen(m) if m else None,
        "semanas": m.semanas() if m else [],
        "siguiente_inicio": siguiente_inicio,
        "siguiente_cobro": _mismo_dia_mes_siguiente(siguiente_inicio),
    })


def _mismo_dia_mes_siguiente(fecha):
    anio, mes_n = (fecha.year + 1, 1) if fecha.month == 12 else (fecha.year, fecha.month + 1)
    for dia in range(fecha.day, 27, -1):
        try:
            return date(anio, mes_n, dia)
        except ValueError:
            continue
    return date(anio, mes_n, min(fecha.day, 28))


@require_POST
def mes_nuevo(request):
    dinero = _importe(request.POST.get("dinero"))
    inicio = _fecha(request.POST.get("inicio"))
    cobro = _fecha(request.POST.get("cobro"))
    if not (dinero and inicio and cobro and cobro > inicio):
        messages.error(request, "Pon cuánto entra y del día que empieza al día del siguiente cobro.")
        return redirect("mes")
    viejo = Mes.objects.filter(inicio__lt=inicio).first()
    with transaction.atomic():
        nuevo = Mes.objects.create(dinero=dinero, inicio=inicio, cobro=cobro)
        if viejo and request.POST.get("copiar"):
            for p in viejo.previstos.all():
                dia = inicio + (p.dia - viejo.inicio)
                if dia > nuevo.fin:
                    continue
                Previsto.objects.create(mes=nuevo, tipo=p.tipo, concepto=p.concepto, tienda=p.tienda,
                                        precio=p.precio, cantidad=p.cantidad, dia=dia)
    messages.success(request, "Mes creado." + (" Revisa lo copiado del anterior." if viejo and request.POST.get("copiar") else ""))
    return _volver_mes(nuevo)


def _datos_previsto(request, m):
    tipo = request.POST.get("tipo")
    concepto = request.POST.get("concepto", "").strip()[:80]
    precio = _importe(request.POST.get("precio"))
    dia = _fecha(request.POST.get("dia"))
    try:
        cantidad = max(1, min(int(request.POST.get("cantidad") or 1), 999))
    except ValueError:
        cantidad = 1
    if tipo not in dict(Previsto.TIPOS) or not concepto or precio is None or dia is None:
        return None
    if not (m.inicio <= dia <= m.fin):
        dia = min(max(dia, m.inicio), m.fin)
    if tipo == Previsto.COMIDA:
        dia = plan_compra.semana_de(m, dia)[0]
    return {"tipo": tipo, "concepto": concepto, "tienda": request.POST.get("tienda", "").strip()[:60],
            "precio": precio, "cantidad": cantidad, "dia": dia}


@require_POST
def previsto_nuevo(request):
    m = _mes_elegido(request)
    datos = _datos_previsto(request, m) if m else None
    if datos is None:
        messages.error(request, "Pon qué es, cuánto cuesta y el día.")
        return _volver_mes(m)
    # semanal: uno cada 7 días hasta fin de mes
    dias = [datos["dia"]]
    if datos["tipo"] == Previsto.OCIO and request.POST.get("semanal"):
        while dias[-1] + timedelta(days=7) <= m.fin:
            dias.append(dias[-1] + timedelta(days=7))
    for dia in dias:
        Previsto.objects.create(mes=m, **{**datos, "dia": dia})
    return _volver_mes(m)


@require_POST
def previsto_guardar(request, pk):
    p = get_object_or_404(Previsto, pk=pk)
    datos = _datos_previsto(request, p.mes)
    if datos is None:
        messages.error(request, "Falta algo: qué es, cuánto cuesta o el día.")
        return _volver_mes(p.mes)
    for campo, valor in datos.items():
        setattr(p, campo, valor)
    p.pagado = bool(request.POST.get("pagado"))
    p.save()
    return _volver_mes(p.mes)


@require_POST
def previsto_borrar(request, pk):
    p = get_object_or_404(Previsto, pk=pk)
    m = p.mes
    p.delete()
    return _volver_mes(m)


def _mes(texto, defecto):
    try:
        a, m = (int(x) for x in texto.split("-"))
        return date(a, m, 1)
    except (AttributeError, ValueError):
        return defecto


def calendario(request):
    hoy = date.today()
    Ticket.objects.filter(confirmado=False, origen="web", creado__lt=timezone.now() - timedelta(days=1)).delete()
    borrador = Ticket.objects.filter(pk=request.GET.get("ticket") or 0, confirmado=False).first()
    elegido = (borrador.fecha if borrador else None) or _fecha(request.GET.get("d")) or hoy
    primero = _mes(request.GET.get("m"), elegido.replace(day=1))
    vista = "anio" if request.GET.get("vista") == "anio" else "mes"
    contexto = {
        "hoy": hoy, "vista": vista, "colores": Evento.COLORES, "dias_cab": cal.DIAS,
        "mes": cal.mes(primero.year, primero.month, hoy, elegido),
        "dia": cal.dia(elegido, hoy, borrador), "resumen": plan_compra.resumen(Mes.actual()),
        "partidas_ticket": Ticket.PARTIDAS,
        "por_revisar": Ticket.objects.filter(confirmado=False, origen="movil"),
    }
    if vista == "anio":
        contexto["anio"] = cal.anio(primero.year, hoy)
    return render(request, "cuentas/calendario.html", contexto)


def _volver(fecha, request=None):
    if request is not None and request.POST.get("volver") == "movil":
        return redirect("/movil/")
    return redirect(f"/?d={fecha:%Y-%m-%d}&m={fecha:%Y-%m}")


@require_POST
def nuevo_evento(request):
    fecha = _fecha(request.POST.get("fecha")) or date.today()
    titulo = request.POST.get("titulo", "").strip()[:120]
    if titulo:
        hora = request.POST.get("hora") or None
        color = request.POST.get("color")
        Evento.objects.create(
            fecha=fecha, hora=hora, titulo=titulo,
            color=color if color in dict(Evento.COLORES) else "salvia",
        )
    return _volver(fecha)


@require_POST
def evento_hecho(request, pk):
    e = get_object_or_404(Evento, pk=pk)
    e.hecho = not e.hecho
    e.save(update_fields=["hecho"])
    return _volver(e.fecha)


@require_POST
def borrar_evento(request, pk):
    e = get_object_or_404(Evento, pk=pk)
    fecha = e.fecha
    e.delete()
    return _volver(fecha)


def _importe_con_signo(texto):
    # con negativos, para los bizum que te devuelven
    texto = (texto or "").strip()
    negativo = texto.startswith("-") or texto.startswith("−")
    valor = _importe(texto.lstrip("-−"))
    if valor is None:
        return None
    return -valor if negativo else valor


def _leer(t, fecha):
    leido = lector.leer(t.archivo.path, fecha)
    t.texto = leido["texto"][:5000]
    t.importe = leido["importe"]
    t.sitio = leido["sitio"]
    t.partida = leido["partida"]
    t.lineas.all().delete()
    for p in leido["productos"]:
        t.lineas.create(nombre=p["nombre"], importe=p["importe"], capricho=clasificador.es_capricho(p["nombre"]))
    t.capricho = sum((l.importe for l in t.lineas.filter(capricho=True)), CERO)
    if leido["fecha"] and abs((leido["fecha"] - fecha).days) <= 40:
        t.fecha = leido["fecha"]


@require_POST
def leer_ticket(request):
    fecha = _fecha(request.POST.get("fecha")) or date.today()
    archivo = request.FILES.get("archivo")
    t = Ticket(fecha=fecha)
    if archivo:
        t.archivo = archivo
        t.save()
        _leer(t, fecha)
    t.save()
    return redirect(f"/?ticket={t.pk}&m={t.fecha:%Y-%m}")


@require_POST
def guardar_ticket(request, pk):
    t = get_object_or_404(Ticket, pk=pk)
    importe = _importe_con_signo(request.POST.get("importe"))
    if importe is None:
        messages.error(request, "Pon el total del ticket, por ejemplo 12,40.")
        if request.POST.get("volver") == "movil":
            return redirect("/movil/")
        return redirect(f"/?ticket={t.pk}&m={t.fecha:%Y-%m}")
    t.fecha = _fecha(request.POST.get("fecha")) or t.fecha
    t.sitio = request.POST.get("sitio", "").strip()[:60]
    partida = request.POST.get("partida")
    t.partida = partida if partida in Ticket.PARTIDAS else "Otro"
    t.importe = importe
    marcadas = set(request.POST.getlist("capricho"))
    for linea in t.lineas.all():
        nuevo = str(linea.pk) in marcadas
        if nuevo != linea.capricho:
            linea.capricho = nuevo
            linea.save(update_fields=["capricho"])
            clasificador.aprender(linea.nombre, nuevo)
    t.capricho = sum((l.importe for l in t.lineas.filter(capricho=True)), CERO)
    t.cubre = "\n".join(request.POST.getlist("cubre"))
    t.confirmado = True
    t.save()
    return _volver(t.fecha, request)


@require_POST
def borrar_ticket(request, pk):
    t = get_object_or_404(Ticket, pk=pk)
    fecha = t.fecha
    if t.archivo:
        t.archivo.delete(save=False)
    t.delete()
    return _volver(fecha, request)


def archivo_ticket(request, pk):
    t = get_object_or_404(Ticket, pk=pk)
    if not t.archivo:
        raise Http404
    return FileResponse(t.archivo.open("rb"))


# --- móvil ---

def api_ping(request):
    pendientes = Ticket.objects.filter(confirmado=False, origen="movil").count()
    return JsonResponse({"app": "presupuesto", "ok": True, "por_revisar": pendientes})


@csrf_exempt
@require_POST
def api_ticket(request):
    uid = (request.POST.get("uid") or "").strip()[:64]
    archivo = request.FILES.get("archivo")
    if not uid or not archivo:
        return JsonResponse({"ok": False, "error": "Falta el archivo o el id"}, status=400)
    if Ticket.objects.filter(uid=uid).exists():
        return JsonResponse({"ok": True, "repetido": True})
    fecha = _fecha(request.POST.get("fecha")) or date.today()
    t = Ticket(fecha=fecha, origen="movil", uid=uid, archivo=archivo)
    t.save()
    _leer(t, fecha)
    t.save()
    return JsonResponse({"ok": True, "id": t.pk, "importe": str(t.importe or ""), "sitio": t.sitio})


def _llave_de(request):
    return request.GET.get("k") or request.COOKIES.get("llave") or ""


def movil(request):
    hoy = date.today()
    pendientes = []
    for t in Ticket.objects.filter(confirmado=False, origen="movil").order_by("-creado"):
        pendientes.append({"t": t, "marcar": cal.para_marcar(t.fecha, t.sitio)})
    hechos = Ticket.objects.filter(confirmado=True).order_by("-fecha", "-creado")[:8]
    return render(request, "cuentas/movil.html", {
        "pendientes": pendientes, "hechos": hechos, "hoy": hoy,
        "resumen": plan_compra.resumen(Mes.actual()), "partidas_ticket": Ticket.PARTIDAS,
        "android": "android" in request.headers.get("User-Agent", "").lower(),
        "enlace_app": _enlace_app(_llave_de(request)),
    })


def movil_manifest(request):
    # en iphone la app de inicio no ve las cookies de safari, por eso va la llave
    from django.templatetags.static import static
    inicio = "/movil/?" + urlencode({"k": _llave_de(request)})
    datos = {
        "name": "Tickets", "short_name": "Tickets", "start_url": inicio, "scope": "/movil/",
        "display": "standalone", "background_color": "#f6f1ea", "theme_color": "#f6f1ea",
        "icons": [{"src": static("cuentas/icono-512.png"), "sizes": "512x512", "type": "image/png"}],
    }
    return JsonResponse(datos, content_type="application/manifest+json")


@require_POST
def movil_subir(request):
    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "No ha llegado ninguna foto.")
        return redirect("/movil/")
    fecha = date.today()
    t = Ticket(fecha=fecha, origen="movil", uid=f"web-{uuid.uuid4()}", archivo=archivo)
    t.save()
    _leer(t, fecha)
    t.save()
    messages.success(request, "Ticket leído. Revisa que esté bien.")
    return redirect("/movil/")


# --- alta de móviles, solo desde el pc ---

PUERTO_MOVIL = 8768


def _ip_pc():
    if settings.PC_IP:
        return settings.PC_IP
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def _huella_cert():
    ruta = settings.MEDIA_ROOT / "tls" / "cert.pem"
    if not ruta.exists():
        return ""
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(ruta.read_text())).hexdigest()


def _direccion():
    return f"https://{_ip_pc()}:{PUERTO_MOVIL}"


def _enlace_app(llave):
    if not llave:
        return ""
    return "tickets://alta?" + urlencode({"u": _direccion(), "k": llave, "h": _huella_cert()})


def moviles(request):
    nuevo = None
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()[:60] or "Móvil"
        m, llave = Movil.nuevo(nombre)
        enlace = f"{_direccion()}/movil/?k={quote(llave)}"
        nuevo = {"m": m, "enlace": enlace,
                 "qr": segno.make(enlace, error="m").svg_inline(scale=6, dark="#2d2926", light="#fffcf7", border=2)}
    return render(request, "cuentas/moviles.html", {
        "moviles": Movil.objects.all(), "nuevo": nuevo, "direccion": _direccion(),
        "huella": _huella_cert(), "llave_vieja": bool(settings.MOVIL_LLAVE),
    })


@require_POST
def borrar_movil(request, pk):
    get_object_or_404(Movil, pk=pk).delete()
    messages.success(request, "Móvil quitado: su llave ya no vale.")
    return redirect("moviles")


def movil_apk(request):
    ruta = settings.MEDIA_ROOT / "app" / "tickets.apk"
    if not ruta.exists():
        raise Http404
    return FileResponse(open(ruta, "rb"), as_attachment=True, filename="tickets.apk",
                        content_type="application/vnd.android.package-archive")
