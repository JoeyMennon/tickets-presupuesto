# tema de la web: modo claro u oscuro y color, guardado en cookies
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

MODOS = [("auto", "Automático"), ("claro", "Claro"), ("oscuro", "Oscuro")]
COLORES = [("rosa", "Rosa"), ("salvia", "Salvia"), ("lavanda", "Lavanda"), ("cielo", "Cielo"), ("miel", "Miel")]
UN_ANIO = 60 * 60 * 24 * 365


def elegido(request):
    modo = request.COOKIES.get("modo")
    color = request.COOKIES.get("color")
    return (modo if modo in dict(MODOS) else "auto", color if color in dict(COLORES) else "rosa")


def contexto(request):
    modo, color = elegido(request)
    return {"tema_modo": modo, "tema_color": color, "tema_modos": MODOS, "tema_colores": COLORES}


@require_POST
def cambiar(request):
    siguiente = request.POST.get("siguiente") or "/"
    if not url_has_allowed_host_and_scheme(siguiente, {request.get_host()}):
        siguiente = "/"
    respuesta = redirect(siguiente)
    modo, color = request.POST.get("modo"), request.POST.get("color")
    if modo in dict(MODOS):
        respuesta.set_cookie("modo", modo, max_age=UN_ANIO, samesite="Lax")
    if color in dict(COLORES):
        respuesta.set_cookie("color", color, max_age=UN_ANIO, samesite="Lax")
    return respuesta
