"""Painéis iniciais próprios dos perfis funcionais da demonstração.

Os construtores reutilizam exclusivamente os querysets de autorização do
backend. A interface organiza dados já permitidos; ela não concede acesso.
"""

from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from contracts.dashboard import build_contract_dashboard
from contracts.executive_dashboard import (
    build_executive_summary,
    build_portfolio_summary,
    build_validity_progress,
)
from contracts.models import IntelligenceReviewStatus
from contracts.services import contracts_exportable_by, contracts_visible_to


def _classification(contract):
    classification = getattr(contract, "intelligence_classification", None)
    if (
        classification is None
        or classification.status != IntelligenceReviewStatus.CONFIRMED
    ):
        return "A confirmar", False
    return classification.get_management_category_display() or "A confirmar", True


def build_auxiliary_dashboard(user):
    """Somente metadados administrativos dos contratos não arquivados."""
    contracts = tuple(
        contracts_visible_to(user)
        .select_related("intelligence_classification")
        .annotate(document_count=Count("documents", distinct=True))
        .order_by("number", "pk")
    )
    rows = []
    document_count = 0
    classification_pending_count = 0
    attention_count = 0
    for contract in contracts:
        category_label, classification_confirmed = _classification(contract)
        issues = []
        if not contract.document_count:
            issues.append("Nenhum documento catalogado")
        if not classification_confirmed:
            issues.append("Classificação gerencial a confirmar")
            classification_pending_count += 1
        document_count += contract.document_count
        attention_count += len(issues)
        rows.append(
            {
                "contract": contract,
                "category_label": category_label,
                "document_count": contract.document_count,
                "issues": tuple(issues),
            }
        )
    return {
        "contract_count": len(contracts),
        "document_count": document_count,
        "classification_pending_count": classification_pending_count,
        "attention_count": attention_count,
        "rows": tuple(rows),
    }


def build_administrative_manager_dashboard(user):
    """Carteira institucional consolidada e classificada."""
    contracts = tuple(
        contracts_visible_to(user)
        .select_related("intelligence_classification")
        .order_by("number", "pk")
    )
    exportable_ids = set(
        contracts_exportable_by(user).values_list("pk", flat=True)
    )
    rows = []
    classification_pending_count = 0
    for contract in contracts:
        category_label, classification_confirmed = _classification(contract)
        if not classification_confirmed:
            classification_pending_count += 1
        rows.append(
            {
                "contract": contract,
                "category_label": category_label,
                "classification_confirmed": classification_confirmed,
                "can_export": contract.pk in exportable_ids,
            }
        )
    return {
        "portfolio": build_portfolio_summary(contracts),
        "classification_pending_count": classification_pending_count,
        "rows": tuple(rows),
    }


def build_contract_manager_dashboard(user, selected_id=None):
    """Visão individual e somente leitura dos contratos vinculados."""
    contracts = contracts_visible_to(user).select_related(
        "intelligence_classification"
    ).order_by("number", "pk")
    if selected_id:
        if not selected_id.isdecimal():
            raise Http404("Contrato não encontrado.")
        selected_contract = get_object_or_404(contracts, pk=selected_id)
    else:
        selected_contract = contracts.first()
    context = {
        "contracts": contracts,
        "selected_contract": selected_contract,
        "dashboard": None,
        "summary": None,
        "validity": None,
        "category_label": "",
        "can_export": False,
    }
    if selected_contract is None:
        return context
    dashboard = build_contract_dashboard(selected_contract)
    context.update(
        {
            "dashboard": dashboard,
            "summary": build_executive_summary(
                selected_contract,
                dashboard,
                today=timezone.localdate(),
            ),
            "validity": build_validity_progress(
                selected_contract,
                today=timezone.localdate(),
            ),
            "category_label": _classification(selected_contract)[0],
            "can_export": contracts_exportable_by(user)
            .filter(pk=selected_contract.pk)
            .exists(),
        }
    )
    return context
