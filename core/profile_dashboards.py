"""Painéis iniciais próprios dos perfis funcionais da demonstração.

Os construtores reutilizam exclusivamente os querysets de autorização do
backend. A interface organiza dados já permitidos; ela não concede acesso.
"""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone

from contracts.calculations import NegativeBalanceError
from contracts.dashboard import build_contract_dashboard
from contracts.executive_dashboard import (
    OPEN_STATUSES,
    build_executive_summary,
    build_portfolio_summary,
    build_validity_progress,
)
from contracts.models import IntelligenceReviewStatus, WorkOrderStatus
from contracts.services import (
    contract_financial_position,
    contracts_exportable_by,
    contracts_visible_to,
    work_orders_visible_to,
)
from contracts.work_order_deadlines import deadline_situation


ZERO = Decimal("0.00")


def _percentage(value, total):
    if not total or total <= 0:
        return ZERO
    return (Decimal(value) * Decimal("100") / Decimal(total)).quantize(
        Decimal("0.01")
    )


def _classification(contract):
    classification = getattr(contract, "intelligence_classification", None)
    if (
        classification is None
        or classification.status != IntelligenceReviewStatus.CONFIRMED
    ):
        return "A confirmar", False
    return classification.get_management_category_display() or "A confirmar", True


def _selected_contract(contracts, selected_id):
    if not selected_id:
        return None
    if not selected_id.isdecimal():
        raise Http404("Contrato não encontrado.")
    return get_object_or_404(contracts, pk=selected_id)


def build_auxiliary_dashboard(user, selected_id=None, selected_status=""):
    """OS abertas e metadados mínimos autorizados para a Auxiliar."""
    contracts_query = (
        contracts_visible_to(user)
        .select_related("intelligence_classification")
        .annotate(document_count=Count("documents", distinct=True))
        .order_by("number", "pk")
    )
    selected_contract = _selected_contract(contracts_query, selected_id)
    contracts = tuple(contracts_query)

    allowed_statuses = tuple(OPEN_STATUSES)
    selected_status = (selected_status or "").strip()
    if selected_status and selected_status not in allowed_statuses:
        raise Http404("Situação de OS não encontrada.")

    work_orders_query = work_orders_visible_to(user).filter(
        status__in=allowed_statuses
    )
    if selected_contract is not None:
        work_orders_query = work_orders_query.filter(contract=selected_contract)
    if selected_status:
        work_orders_query = work_orders_query.filter(status=selected_status)

    today = timezone.localdate()
    work_order_rows = []
    total_hours = Decimal("0")
    quantities = defaultdict(Decimal)
    total_value = ZERO
    overdue_count = 0
    no_deadline_count = 0
    for work_order in work_orders_query.order_by(
        "deadline", "contract__number", "opening_date", "number", "pk"
    ):
        situation = deadline_situation(work_order, today)
        is_overdue = situation.code == "late"
        overdue_count += int(is_overdue)
        no_deadline_count += int(work_order.deadline is None)
        if work_order.hours is not None:
            total_hours += work_order.hours
        elif work_order.quantity is not None:
            quantities[work_order.unit_name] += work_order.quantity
        total_value += work_order.total_value
        work_order_rows.append(
            {
                "work_order": work_order,
                "situation": situation,
                "is_overdue": is_overdue,
            }
        )
    work_order_rows.sort(
        key=lambda row: (
            not row["is_overdue"],
            row["work_order"].deadline or date.max,
            row["work_order"].contract.number,
            row["work_order"].pk,
        )
    )

    metadata_rows = []
    document_count = 0
    classification_pending_count = 0
    metadata_attention_count = 0
    for contract in contracts:
        category_label, classification_confirmed = _classification(contract)
        issues = []
        if not contract.document_count:
            issues.append("Nenhum documento catalogado")
        if not classification_confirmed:
            issues.append("Classificação gerencial a confirmar")
            classification_pending_count += 1
        document_count += contract.document_count
        metadata_attention_count += len(issues)
        metadata_rows.append(
            {
                "contract": contract,
                "category_label": category_label,
                "document_count": contract.document_count,
                "issues": tuple(issues),
            }
        )

    return {
        "contracts": contracts,
        "selected_contract": selected_contract,
        "selected_status": selected_status,
        "status_choices": tuple(
            (value, label)
            for value, label in WorkOrderStatus.choices
            if value in allowed_statuses
        ),
        "contract_count": len(contracts),
        "document_count": document_count,
        "classification_pending_count": classification_pending_count,
        "metadata_attention_count": metadata_attention_count,
        "open_count": len(work_order_rows),
        "overdue_count": overdue_count,
        "no_deadline_count": no_deadline_count,
        "total_hours": total_hours,
        "quantity_summaries": tuple(
            {"unit": unit, "quantity": quantity}
            for unit, quantity in sorted(quantities.items())
        ),
        "total_value": total_value,
        "work_order_rows": tuple(work_order_rows),
        # Mantido para as notificações administrativas já existentes.
        "rows": tuple(metadata_rows),
    }


def build_administrative_manager_dashboard(user, selected_id=None):
    """Carteira geral, consolidada e classificada do Gestor Administrativo."""
    contracts_query = (
        contracts_visible_to(user)
        .select_related("intelligence_classification")
        .order_by("number", "pk")
    )
    selected_contract = _selected_contract(contracts_query, selected_id)
    contracts = tuple(contracts_query)
    scope_contracts = (selected_contract,) if selected_contract else contracts
    exportable_ids = set(
        contracts_exportable_by(user).values_list("pk", flat=True)
    )

    totals = {
        "committed_budget": ZERO,
        "committed": ZERO,
        "executed": ZERO,
        "invoiced": ZERO,
        "paid": ZERO,
        "balance": ZERO,
        "inconsistent_count": 0,
    }
    rows = []
    classification_pending_count = 0
    for contract in scope_contracts:
        category_label, classification_confirmed = _classification(contract)
        if not classification_confirmed:
            classification_pending_count += 1
        financial = None
        inconsistent = False
        try:
            financial = contract_financial_position(contract)
        except NegativeBalanceError:
            inconsistent = True
            totals["inconsistent_count"] += 1
        if financial is not None:
            values = {
                "committed_budget": financial.total_committed_budget.value,
                "committed": financial.committed_value.value,
                "executed": financial.executed_value.value,
                "invoiced": financial.invoiced_gross_value.value,
                "paid": financial.paid_value.value,
                "balance": financial.contract_balance.value,
            }
            for key, value in values.items():
                totals[key] += value
        else:
            values = {key: ZERO for key in totals if key != "inconsistent_count"}
        rows.append(
            {
                "contract": contract,
                "category_label": category_label,
                "classification_confirmed": classification_confirmed,
                "can_export": contract.pk in exportable_ids,
                "financial": values,
                "executed_percentage": _percentage(
                    values["executed"], contract.current_value
                ),
                "paid_percentage": _percentage(values["paid"], contract.current_value),
                "inconsistent": inconsistent,
            }
        )

    portfolio = build_portfolio_summary(scope_contracts)
    financial_rows = tuple(
        {
            "label": label,
            "value": totals[key],
            "percentage": _percentage(totals[key], portfolio.current_value),
            "tone": tone,
        }
        for key, label, tone in (
            ("committed", "Comprometido em OS", "reserved"),
            ("executed", "Executado", "executed"),
            ("invoiced", "Faturado", "invoiced"),
            ("paid", "Pago", "paid"),
        )
    )
    category_rows = tuple(
        {
            "summary": category,
            "percentage": _percentage(
                category.current_value, portfolio.current_value
            ),
        }
        for category in portfolio.categories
    )

    work_orders = tuple(
        work_orders_visible_to(user)
        .filter(contract__in=scope_contracts)
        .order_by("contract__number", "opening_date", "number", "pk")
    )
    status_counts = Counter(work_order.status for work_order in work_orders)
    status_labels = dict(WorkOrderStatus.choices)
    status_rows = tuple(
        {
            "value": value,
            "label": status_labels[value],
            "count": status_counts[value],
            "percentage": _percentage(status_counts[value], len(work_orders)),
        }
        for value, _label in WorkOrderStatus.choices
        if status_counts[value]
    )
    today = timezone.localdate()
    open_work_orders = tuple(
        work_order for work_order in work_orders if work_order.status in OPEN_STATUSES
    )
    overdue_work_orders = tuple(
        work_order
        for work_order in open_work_orders
        if work_order.deadline is not None and work_order.deadline < today
    )

    return {
        "contracts": contracts,
        "selected_contract": selected_contract,
        "scope_label": (
            f"Contrato {selected_contract.number}"
            if selected_contract
            else "Todos os contratos"
        ),
        "portfolio": portfolio,
        "financial_totals": totals,
        "financial_rows": financial_rows,
        "classification_pending_count": classification_pending_count,
        "category_rows": category_rows,
        "work_order_count": len(work_orders),
        "open_count": len(open_work_orders),
        "overdue_count": len(overdue_work_orders),
        "overdue_work_orders": overdue_work_orders,
        "status_rows": status_rows,
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
