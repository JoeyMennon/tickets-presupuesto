from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def euros(valor):
    if valor is None:
        return ""
    texto = f"{Decimal(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto} €"


@register.filter
def neg(valor):
    return -valor


@register.filter
def coma(valor):
    if valor is None:
        return ""
    return f"{Decimal(valor):.2f}".replace(".", ",")
