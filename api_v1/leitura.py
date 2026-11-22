"""Leitura humana dos rascunhos da IA (Sprint 61).

Transforma os dados técnicos do rascunho (JSON) em linhas escritas em
português, para que o fiscal confira a proposta sem ler código. Não altera
o rascunho nem as regras de confirmação: só muda a forma de mostrar.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from .drafts import FORM_CLASSES

SITUACOES = {
    "NOVO": "Novo",
    "IGUAL": "Igual ao atual",
    "ALTERADO": "Alterado",
    "DIVERGENTE": "Diferente do atual — conferir",
    "AUSENTE": "A IA deixou em branco",
    "PENDENTE_DE_CONFIRMACAO": "Precisa de confirmação",
    "NAO_CONFIAVEL": "Pouco confiável — conferir",
}

POSICAO_FINANCEIRA = (
    ("total_committed_budget", "Total empenhado"),
    ("committed_value", "Comprometido em OS"),
    ("executed_value", "Executado"),
    ("invoiced_gross_value", "Faturado (bruto)"),
    ("paid_value", "Pago"),
    ("contract_balance", "Saldo do contrato"),
)

_CAMPOS_DINHEIRO = ("value", "amount", "valor")
_VAZIO = "—"


def _rotulo(entity_type, field):
    form_class = FORM_CLASSES.get(entity_type)
    if form_class is not None and field in form_class.base_fields:
        label = form_class.base_fields[field].label
        if label:
            return str(label)
        model = form_class._meta.model
        try:
            return str(model._meta.get_field(field).verbose_name).capitalize()
        except Exception:  # noqa: BLE001 - campo fora do modelo: usa o nome
            pass
    return field.replace("_", " ").capitalize()


def reais(valor):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return str(valor)
    texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def _numero(valor):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return str(valor)
    if numero == numero.to_integral_value():
        return f"{int(numero):,}".replace(",", ".")
    return f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(valor):
    texto = str(valor)
    for formato in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(texto, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return texto


def valor_legivel(field, valor):
    """Mostra um valor como o fiscal leria: reais, datas e números em pt-BR."""
    if valor is None or valor == "":
        return _VAZIO
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, (list, tuple)):
        return ", ".join(valor_legivel(field, item) for item in valor) or _VAZIO
    if isinstance(valor, dict):
        return "; ".join(f"{k}: {valor_legivel(k, v)}" for k, v in valor.items()) or _VAZIO
    nome = field.lower()
    if "date" in nome or "data" in nome:
        return _data(valor)
    if any(parte in nome for parte in _CAMPOS_DINHEIRO) and "status" not in nome:
        return reais(valor)
    if any(parte in nome for parte in ("quantity", "hours", "quantidade", "horas")):
        return _numero(valor)
    return str(valor)


def linhas_da_proposta(draft):
    """Uma linha por campo: nome em português, hoje, proposto e situação."""
    linhas = []
    for row in draft.comparison or []:
        field = str(row.get("field", ""))
        linhas.append({
            "campo": _rotulo(draft.entity_type, field),
            "hoje": valor_legivel(field, row.get("current")),
            "proposto": valor_legivel(field, row.get("proposed")),
            "situacao": SITUACOES.get(row.get("classification"), str(row.get("classification", ""))),
            "importante": bool(row.get("critical")),
            "confirmacao_obrigatoria": row.get("source_precedence") == "CONFIRMACAO_OBRIGATORIA",
        })
    return linhas


def fontes_legiveis(draft):
    """Cada evidência como frase curta: fonte, referência e trecho."""
    fontes = []
    for entry in draft.evidence or []:
        if not isinstance(entry, dict):
            continue
        field = str(entry.get("field", "") or "")
        fontes.append({
            "fonte": entry.get("filename") or entry.get("source") or "Fonte não informada",
            "referencia": entry.get("reference", ""),
            "trecho": entry.get("excerpt", ""),
            "campo": _rotulo(draft.entity_type, field) if field else "",
            "valor": valor_legivel(field, entry.get("extracted_value")) if entry.get("extracted_value") not in (None, "") else "",
        })
    return fontes


def resultado_legivel(draft):
    """Resultado da verificação feita pelo sistema depois da aprovação."""
    resultado = draft.consistency_result or {}
    if not resultado:
        return None
    posicao = resultado.get("financial_position") or {}
    valores = []
    for chave, rotulo in POSICAO_FINANCEIRA:
        item = posicao.get(chave)
        valor = item.get("value") if isinstance(item, dict) else item
        if valor not in (None, ""):
            valores.append({"rotulo": rotulo, "valor": reais(valor)})
    return {
        "conferido": resultado.get("status") == "VALIDADO",
        "quando": _data(resultado.get("validated_at", "")) if resultado.get("validated_at") else "",
        "prestacao_confere": resultado.get("accountability_matches"),
        "valores": valores,
    }
