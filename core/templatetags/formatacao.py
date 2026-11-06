"""Filtros de exibição. Não alteram valores gravados, apenas a apresentação."""

from decimal import Decimal, InvalidOperation

from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def quantidade(value):
    """Exibe quantidades com no mínimo 2 e no máximo 4 casas decimais.

    Casas significativas nunca são ocultadas: 20.0000 vira "20,00" e
    12.3456 continua "12,3456".
    """
    if value is None or value == "":
        return value
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value
    exponent = number.normalize().as_tuple().exponent
    places = min(4, max(2, -exponent if isinstance(exponent, int) else 2))
    return number_format(number, decimal_pos=places, use_l10n=True, force_grouping=True)


@register.filter
def cnpj_cpf(value):
    """Aplica a máscara de CNPJ (14 dígitos) ou CPF (11 dígitos)."""
    if not value:
        return value
    digits = "".join(character for character in str(value) if character.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return value
