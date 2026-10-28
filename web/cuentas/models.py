import hashlib
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.db import models


class Mes(models.Model):

    inicio = models.DateField()
    cobro = models.DateField(help_text="Día del siguiente cobro; el mes acaba el día anterior")
    dinero = models.DecimalField(max_digits=8, decimal_places=2, help_text="Lo que entra al empezar")

    class Meta:
        ordering = ["-inicio"]

    def __str__(self):
        return f"{self.inicio:%d/%m} al {self.fin:%d/%m/%Y}"

    @property
    def fin(self):
        return self.cobro - timedelta(days=1)

    @classmethod
    def actual(cls, hoy=None):
        hoy = hoy or date.today()
        return cls.objects.filter(inicio__lte=hoy, cobro__gt=hoy).first() or cls.objects.first()

    def semanas(self):
        # semanas de 7 días desde el cobro, lo que sobra va con la última
        tramos, dia = [], self.inicio
        while dia <= self.fin:
            hasta = dia + timedelta(days=6)
            if (self.fin - hasta).days < 7:
                hasta = self.fin
            tramos.append((dia, min(hasta, self.fin)))
            dia = hasta + timedelta(days=1)
        return tramos


class Previsto(models.Model):

    FIJO, OCIO, COMIDA = "fijo", "ocio", "comida"
    TIPOS = [(FIJO, "Fijo"), (OCIO, "Ocio"), (COMIDA, "Comida")]

    mes = models.ForeignKey(Mes, on_delete=models.CASCADE, related_name="previstos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    concepto = models.CharField(max_length=80)
    tienda = models.CharField(max_length=60, blank=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    cantidad = models.PositiveSmallIntegerField(default=1)
    dia = models.DateField()
    pagado = models.BooleanField(default=False, help_text="Ya pagado y apuntado en el banco")

    class Meta:
        ordering = ["dia", "id"]

    def __str__(self):
        return self.concepto

    @property
    def importe(self):
        return self.precio * self.cantidad

    @property
    def clave(self):
        return f"p{self.pk}"


CERO = Decimal("0.00")


class Evento(models.Model):

    COLORES = [
        ("salvia", "Salvia"),
        ("rosa", "Rosa"),
        ("lavanda", "Lavanda"),
        ("miel", "Miel"),
        ("cielo", "Cielo"),
    ]

    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    titulo = models.CharField(max_length=120)
    color = models.CharField(max_length=10, choices=COLORES, default="salvia")
    hecho = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora", "creado"]

    def __str__(self):
        return f"{self.fecha} {self.titulo}"


class Ticket(models.Model):

    PARTIDAS = ["Súper", "Caprichos", "Cafés", "Comida fuera", "Ocio", "Pan", "Fijo", "Otro"]

    fecha = models.DateField()
    sitio = models.CharField(max_length=60, blank=True)
    partida = models.CharField(max_length=30, default="Súper")
    importe = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    capricho = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                   help_text="Parte del importe que es capricho, sacada de las líneas")
    cubre = models.TextField(blank=True, help_text="Claves de lo previsto que paga este ticket, una por línea")
    archivo = models.FileField(upload_to="tickets/", blank=True)
    texto = models.TextField(blank=True, help_text="Lo que se ha leído del ticket")
    confirmado = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, default="web")
    uid = models.CharField(max_length=64, unique=True, null=True, blank=True, help_text="Id que pone la app del móvil")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "creado"]

    def __str__(self):
        return f"{self.fecha} {self.sitio} {self.importe}"

    def claves(self):
        return [c for c in self.cubre.splitlines() if c]

    def partes(self):
        total = self.importe or CERO
        capricho = min(self.capricho or CERO, total) if total > 0 else CERO
        if self.partida == "Caprichos" or capricho <= 0:
            return [(self.partida, total)]
        resto = total - capricho
        return [(self.partida, resto), ("Caprichos", capricho)] if resto else [("Caprichos", capricho)]


class LineaTicket(models.Model):

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="lineas")
    nombre = models.CharField(max_length=80)
    importe = models.DecimalField(max_digits=8, decimal_places=2)
    capricho = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]


class Producto(models.Model):

    clave = models.CharField(max_length=80, unique=True)
    capricho = models.BooleanField()

    def __str__(self):
        return f"{self.clave}: {'capricho' if self.capricho else 'comida'}"


class Movil(models.Model):
    # solo se guarda el hash de la llave

    nombre = models.CharField(max_length=60)
    huella = models.CharField(max_length=64, unique=True)
    creado = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["creado"]

    def __str__(self):
        return self.nombre

    @staticmethod
    def huella_de(llave):
        return hashlib.sha256(llave.encode()).hexdigest()

    @classmethod
    def nuevo(cls, nombre):
        # la llave solo se ve aquí, luego solo queda el hash
        llave = secrets.token_urlsafe(32)
        return cls.objects.create(nombre=nombre, huella=cls.huella_de(llave)), llave
