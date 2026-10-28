from django.urls import path

from . import views

urlpatterns = [
    path("", views.calendario, name="calendario"),
    path("mes/", views.mes, name="mes"),
    path("mes/nuevo/", views.mes_nuevo, name="mes_nuevo"),
    path("mes/previsto/", views.previsto_nuevo, name="previsto_nuevo"),
    path("mes/previsto/<int:pk>/", views.previsto_guardar, name="previsto_guardar"),
    path("mes/previsto/<int:pk>/borrar/", views.previsto_borrar, name="previsto_borrar"),
    path("api/ping/", views.api_ping, name="api_ping"),
    path("api/ticket/", views.api_ticket, name="api_ticket"),
    path("movil/", views.movil, name="movil"),
    path("movil/tickets.apk", views.movil_apk, name="movil_apk"),
    path("movil/manifest.webmanifest", views.movil_manifest, name="movil_manifest"),
    path("movil/subir/", views.movil_subir, name="movil_subir"),
    path("moviles/", views.moviles, name="moviles"),
    path("moviles/<int:pk>/borrar/", views.borrar_movil, name="borrar_movil"),
    path("ticket/", views.leer_ticket, name="leer_ticket"),
    path("ticket/<int:pk>/guardar/", views.guardar_ticket, name="guardar_ticket"),
    path("ticket/<int:pk>/borrar/", views.borrar_ticket, name="borrar_ticket"),
    path("ticket/<int:pk>/archivo/", views.archivo_ticket, name="archivo_ticket"),
    path("evento/", views.nuevo_evento, name="nuevo_evento"),
    path("evento/<int:pk>/hecho/", views.evento_hecho, name="evento_hecho"),
    path("evento/<int:pk>/borrar/", views.borrar_evento, name="borrar_evento"),
]
