"""Análise de divergências para o MCP remoto (Sprint 29).

Compara valores que a IA leu num documento com o registro gravado, usando
somente o escopo de **leitura** da pessoa. Não grava nada, não cria rascunho
e não decide nada: só aponta igual, diferente ou ausente, campo a campo.
"""

import re
from decimal import Decimal, InvalidOperation

from django.core.exceptions import FieldDoesNotExist

from contracts.services import (
    allocations_visible_to, commitments_visible_to, contracts_visible_to,
    executions_visible_to, invoices_visible_to, items_visible_to,
    payments_visible_to, work_orders_visible_to,
)

from .drafts import CRITICAL_FIELDS, FORM_CLASSES, _current_values, _target_contract
from .models import AssistantDraft

MAX_FIELDS = 50

VISIBLE_QUERYSETS = {
    AssistantDraft.EntityType.CONTRACT: contracts_visible_to,
    AssistantDraft.EntityType.ITEM: items_visible_to,
    AssistantDraft.EntityType.COMMITMENT: commitments_visible_to,
    AssistantDraft.EntityType.WORK_ORDER: work_orders_visible_to,
    AssistantDraft.EntityType.ALLOCATION: allocations_visible_to,
    AssistantDraft.EntityType.EXECUTION: executions_visible_to,
    AssistantDraft.EntityType.INVOICE: invoices_visible_to,
    AssistantDraft.EntityType.PAYMENT: payments_visible_to,
}

NUMBER = re.compile(r"^-?(R\$\s*)?[\d.,]+$")
BR_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


class AnalysisError(Exception):
    """Erro com mensagem segura para a IA."""


def normalize(value):
    """Forma comparável: números sem formatação brasileira, datas em ISO, texto sem espaços extras."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = " ".join(str(value).split())
    date = BR_DATE.match(text)
    if date:
        return f"{date.group(3)}-{date.group(2)}-{date.group(1)}"
    if NUMBER.match(text):
        digits = text.replace("R$", "").strip()
        if "," in digits:
            digits = digits.replace(".", "").replace(",", ".")
        try:
            return format(Decimal(digits).normalize(), "f")
        except InvalidOperation:
            return text.casefold()
    return text.casefold()


def analyze_divergences(*, user, entity_type, target_id, document_values):
    """Devolve ``(resultado, contrato)`` sem alterar nenhum dado."""
    queryset_factory = VISIBLE_QUERYSETS.get(entity_type)
    if queryset_factory is None:
        raise AnalysisError("Tipo de registro inválido.")
    if not isinstance(document_values, dict) or not document_values:
        raise AnalysisError("Informe os valores lidos no documento (campo: valor).")
    if len(document_values) > MAX_FIELDS:
        raise AnalysisError(f"Envie no máximo {MAX_FIELDS} campos por análise.")
    allowed = set(FORM_CLASSES[entity_type].Meta.fields)
    unknown = sorted(set(document_values) - allowed)
    if unknown:
        raise AnalysisError(f"Campos desconhecidos: {', '.join(unknown)}. Válidos: {', '.join(sorted(allowed))}.")
    target = queryset_factory(user).filter(pk=target_id).first()
    if target is None:
        raise AnalysisError("Registro não encontrado ou sem permissão.")
    try:
        current = _current_values(target, document_values)
    except FieldDoesNotExist as exc:
        raise AnalysisError("Campo inválido para este registro.") from exc
    critical_fields = CRITICAL_FIELDS.get(entity_type, set())
    rows, counts = [], {}
    for field, read_value in document_values.items():
        system_value = current.get(field)
        system_norm, document_norm = normalize(system_value), normalize(read_value)
        if document_norm == system_norm:
            classification = "IGUAL"
        elif document_norm == "":
            classification = "AUSENTE_NO_DOCUMENTO"
        elif system_norm == "":
            classification = "VAZIO_NO_SISTEMA"
        else:
            classification = "DIFERENTE"
        counts[classification] = counts.get(classification, 0) + 1
        rows.append({
            "field": field, "system_value": system_value, "document_value": read_value,
            "classification": classification, "critical": field in critical_fields,
        })
    critical_differences = [row["field"] for row in rows
                            if row["critical"] and row["classification"] != "IGUAL"]
    return {
        "entity_type": entity_type, "target_id": target.pk,
        "fields": rows, "classification_counts": counts,
        "critical_differences": critical_differences,
        "written": False,
        "notice": (
            "Análise informativa: nada foi gravado. Para corrigir, proponha um rascunho "
            "(exige o escopo de propor) e a pessoa confirma na interface web. Não "
            "constitui atesto, homologação, liquidação ou autorização de pagamento."
        ),
    }, _target_contract(target)
