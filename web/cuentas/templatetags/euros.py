from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def euros(valor):
    """1234.5 -> '1.234,50 €'"""
    if valor is None:
        return ""
    texto = f"{Decimal(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{texto} €"


@register.filter
def neg(valor):
    return -valor


@register.filter
def coma(valor):
    """8.67 -> '8,67' para dejarlo escrito en un campo."""
    if valor is None:
        return ""
    return f"{Decimal(valor):.2f}".replace(".", ",")
