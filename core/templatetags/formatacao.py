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
def barra(value):
    """Largura visual de uma barra de progresso, de 0 a 100 (Sprint 35).

    Só apresentação: o percentual escrito ao lado continua o valor real
    (pode passar de 100%), mas a barra nunca estoura a caixa.
    """
    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    try:
        number = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    if not number.is_finite():
        return 0
    return int(min(max(number, Decimal("0")), Decimal("100")).to_integral_value(ROUND_HALF_UP))


@register.filter
def proporcao(value, total):
    """Altura/largura (0 a 100) de um valor em relação ao maior valor do gráfico (Sprint 37)."""
    from decimal import Decimal, InvalidOperation

    try:
        value, total = Decimal(str(value)), Decimal(str(total))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    if total <= 0 or value <= 0:
        return 0
    return barra(value * Decimal("100") / total)


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


CHECK_STATUS_LABELS = {
    "CONFERIDA": ("Conferida", "status-success"),
    "OK": ("OK", "status-success"),
    "NAO_APLICAVEL": ("Não se aplica", "status-neutral"),
    "COM_PENDENCIA": ("Pendente de conferência", "status-warning"),
    "COM_DIVERGENCIA": ("Com divergência", "status-danger"),
    "POSSIVEL_DUPLICIDADE": ("Possível duplicidade", "status-danger"),
    "BLOQUEADA": ("Bloqueada", "status-danger"),
}


@register.filter
def status_conferencia(value):
    """Texto legível para os códigos da conferência de Nota Fiscal."""
    return CHECK_STATUS_LABELS.get(value, (value, ""))[0]


@register.filter
def tom_conferencia(value):
    """Classe de cor (status-pill) para os códigos da conferência de Nota Fiscal."""
    return CHECK_STATUS_LABELS.get(value, ("", "status-neutral"))[1]
