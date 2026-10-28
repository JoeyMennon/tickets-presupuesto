"""Desde la wifi solo se entra a la parte del móvil: por https, en el puerto 8768 y con la llave de un móvil dado de alta."""
import ipaddress
import secrets

from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseForbidden, HttpResponseNotFound

ABIERTO = ("/api/", "/movil/", "/ticket/", "/static/")
DIEZ_ANIOS = 10 * 365 * 24 * 3600


def _vale(llave):
    """La llave vieja del .env o la de un móvil dado de alta desde el PC."""
    if not llave:
        return False
    if settings.MOVIL_LLAVE and secrets.compare_digest(llave, settings.MOVIL_LLAVE):
        return True
    from .models import Movil
    return Movil.objects.filter(huella=Movil.huella_de(llave)).update(ultimo_uso=timezone.now()) > 0


class SoloMovil:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            ip = ipaddress.ip_address(request.META.get("REMOTE_ADDR", ""))
        except ValueError:
            return HttpResponseForbidden()
        if ip.is_loopback:
            return self.get_response(request)
        if not ip.is_private or not request.is_secure():
            return HttpResponseForbidden()
        if not request.path.startswith(ABIERTO):
            return HttpResponseNotFound()
        if request.path.startswith("/static/"):
            return self.get_response(request)

        de_url = request.GET.get("k", "")
        llave = request.headers.get("X-Llave") or de_url or request.COOKIES.get("llave") or ""
        if not _vale(llave):
            return HttpResponseForbidden("Sin llave")
        respuesta = self.get_response(request)
        if de_url:
            respuesta.set_cookie("llave", de_url, max_age=DIEZ_ANIOS, httponly=True, samesite="Lax", secure=True)
        return respuesta
