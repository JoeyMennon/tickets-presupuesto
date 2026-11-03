from datetime import date
from decimal import Decimal

from django.test import TestCase

from . import lector
from .models import Mes, Previsto, Ticket, Tienda


class EditarTicket(TestCase):

    def setUp(self):
        self.mes = Mes.objects.create(inicio=date(2026, 10, 28), cobro=date(2026, 11, 28), dinero=Decimal("430"))
        self.pan = Previsto.objects.create(mes=self.mes, tipo="comida", concepto="Pan", precio=Decimal("2"), dia=date(2026, 11, 1))
        self.t = Ticket.objects.create(fecha=date(2026, 11, 1), sitio="Casa", partida="Casa", importe=Decimal("180"),
                                       cubre=self.pan.clave, confirmado=True)

    def test_se_abre_ya_guardado(self):
        r = self.client.get(f"/?ticket={self.t.pk}&m=2026-11")
        self.assertContains(r, "editar gasto")
        self.assertContains(r, 'value="Casa" checked')
        # lo que ya cubre sigue saliendo y marcado
        self.assertContains(r, f'value="{self.pan.clave}" checked')

    def test_guardar_no_pierde_la_partida(self):
        self.client.post(f"/ticket/{self.t.pk}/guardar/", {
            "importe": "175,50", "fecha": "2026-11-02", "sitio": "Casa", "partida": "Casa", "cubre": self.pan.clave})
        self.t.refresh_from_db()
        self.assertEqual(self.t.partida, "Casa")
        self.assertEqual(self.t.importe, Decimal("175.50"))
        self.assertEqual(self.t.fecha, date(2026, 11, 2))
        self.assertEqual(self.t.claves(), [self.pan.clave])

    def test_desde_el_movil(self):
        r = self.client.get(f"/movil/?editar={self.t.pk}")
        self.assertContains(r, "editar gasto")
        self.assertContains(r, "Borrar gasto")


class Tema(TestCase):

    def test_cookie_y_pagina(self):
        r = self.client.post("/tema/", {"modo": "oscuro", "siguiente": "/movil/"})
        self.assertEqual(r.cookies["modo"].value, "oscuro")
        r = self.client.get("/movil/")
        self.assertContains(r, 'data-modo="oscuro" data-color="rosa"')

    def test_no_redirige_fuera(self):
        r = self.client.post("/tema/", {"color": "cielo", "siguiente": "https://otra.web/"})
        self.assertEqual(r["Location"], "/")

    def test_valor_raro(self):
        self.client.cookies["modo"] = "<script>"
        self.assertContains(self.client.get("/movil/"), 'data-modo="auto"')


class Lector(TestCase):
    REF = date(2026, 11, 3)

    def test_ticket_de_cafeteria(self):
        r = lector.analizar("Bruma Coffee\n28 de octubre de 2026\nFlat White 240 ml x 1 3,00€A\n"
                            "Cookie x 1 2,00€A\nTotal 5,00€\nNIF: 12345678Z", self.REF)
        self.assertEqual(r["importe"], Decimal("5.00"))
        self.assertEqual(r["fecha"], date(2026, 10, 28))
        self.assertEqual((r["sitio"], r["partida"]), ("Bruma Coffee", "Cafés"))
        self.assertEqual([p["nombre"] for p in r["productos"]], ["Flat White", "Cookie"])

    def test_precios_sin_cero_y_tienda_mal_leida(self):
        r = lector.analizar("RLCAMPO VIGO\nBROCOLI FILMADO ,95 C\nCALABACIN ,98 C\nTOT 1, 93", self.REF)
        self.assertEqual(r["importe"], Decimal("1.93"))
        self.assertEqual(r["sitio"], "Alcampo")
        self.assertEqual(sum(p["importe"] for p in r["productos"]), Decimal("1.93"))

    def test_captura_sin_coma(self):
        r = lector.analizar("TIENDA ONLINE\n210 €\nmartes, 3 nov a las 11:13", self.REF)
        self.assertEqual(r["importe"], Decimal("2.10"))
        self.assertEqual(r["fecha"], date(2026, 11, 3))
        self.assertEqual(r["productos"], [])

    def test_comercio_con_etiqueta(self):
        r = lector.analizar("Datos de la operación\nIMPORTE 4,00 €\nComercio: DULCES ROSA (ESPAÑA)\nFecha: 29/10/2026 10:40", self.REF)
        self.assertEqual(r["sitio"], "Dulces Rosa")
        self.assertEqual(r["importe"], Decimal("4.00"))

    def test_fecha_del_futuro_no_vale(self):
        r = lector.analizar("Total 3,00\n01/01/2030\n28/10/2026", self.REF)
        self.assertEqual(r["fecha"], date(2026, 10, 28))

    def test_aprende_la_tienda(self):
        crudo = "Datos de la operación\nIMPORTE 4,00 €\nComercio: DULCES ROSA (ESPAÑA)"
        t = Ticket.objects.create(fecha=self.REF, importe=Decimal("4"), texto=crudo)
        self.client.post(f"/ticket/{t.pk}/guardar/", {"importe": "4", "sitio": "Dulces Rosa", "partida": "Caprichos"})
        self.assertTrue(Tienda.objects.exists())
        r = lector.analizar(crudo, self.REF)
        self.assertEqual((r["sitio"], r["partida"]), ("Dulces Rosa", "Caprichos"))
