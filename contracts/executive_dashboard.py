"""Dashboard executivo do contrato (Sprint 37; referência: FiscalSema Light).

Somente leitura. Reúne, a partir do motor financeiro e do painel já
existentes, a visão gerencial do contrato:

- vigência decorrida x comprometido, executado, faturado e pago;
- situação das OS (com percentuais) e horas informadas nas OS;
- evolução mensal de executado, faturado e pago.

Nada é estimado: meses sem registro valem zero.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from .calculations import NegativeBalanceError
from .models import (
    ContractItemUnit,
    ContractManagementCategory,
    Payment,
    WorkOrderExecution,
    WorkOrderStatus,
)
from .periods import period_for_date, calendar_year_periods
from .services import contract_financial_position

MONTHLY_EVOLUTION_MONTHS = 12
OPEN_STATUSES = (
    WorkOrderStatus.OPEN, WorkOrderStatus.SIGNED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.SUSPENDED,
)


def _percentage(value, total):
    if not total or total <= 0:
        return Decimal("0.00")
    return (Decimal(value) * Decimal("100") / Decimal(total)).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class ProgressRow:
    label: str
    value: Decimal
    percentage: Decimal
    tone: str


@dataclass(frozen=True)
class StatusRow:
    label: str
    count: int
    percentage: Decimal


@dataclass(frozen=True)
class HourSummary:
    open_hours: Decimal
    delivered_period: object | None
    delivered_hours: Decimal
    delivered_count: int
    spent_hours: Decimal
    with_spent_count: int


@dataclass(frozen=True)
class ValidityProgress:
    total_days: int
    elapsed_days: int
    remaining_days: int
    percentage: Decimal
    has_started: bool
    has_ended: bool


@dataclass(frozen=True)
class MonthlyEntry:
    label: str
    executed: Decimal
    invoiced: Decimal
    paid: Decimal


@dataclass(frozen=True)
class MonthlyEvolution:
    entries: tuple
    max_value: Decimal
    total_executed: Decimal
    total_invoiced: Decimal
    total_paid: Decimal


@dataclass(frozen=True)
class ExecutiveSummary:
    financial_progress: tuple
    status_rows: tuple
    work_order_count: int
    open_count: int
    completed_count: int
    commitment_count: int
    active_commitment_count: int
    has_hour_items: bool
    hours: HourSummary
    open_rows: tuple


@dataclass(frozen=True)
class PortfolioCategorySummary:
    category: str
    label: str
    contract_count: int
    current_value: Decimal
    committed_budget: Decimal
    paid_value: Decimal
    contract_balance: Decimal
    inconsistent_count: int


@dataclass(frozen=True)
class PortfolioSummary:
    categories: tuple
    contract_count: int
    current_value: Decimal
    committed_budget: Decimal
    paid_value: Decimal
    contract_balance: Decimal


def build_portfolio_summary(contracts):
    """Agrupa contratos visíveis sem misturar categoria gerencial e medição."""
    labels = dict(ContractManagementCategory.choices)
    grouped = {}
    zero = Decimal("0.00")
    for contract in contracts:
        classification = getattr(contract, "intelligence_classification", None)
        category = classification.management_category if classification else ""
        values = grouped.setdefault(
            category,
            {
                "contract_count": 0,
                "current_value": zero,
                "committed_budget": zero,
                "paid_value": zero,
                "contract_balance": zero,
                "inconsistent_count": 0,
            },
        )
        values["contract_count"] += 1
        values["current_value"] += contract.current_value
        try:
            position = contract_financial_position(contract)
        except NegativeBalanceError:
            values["inconsistent_count"] += 1
            continue
        values["committed_budget"] += position.total_committed_budget.value
        values["paid_value"] += position.paid_value.value
        values["contract_balance"] += position.contract_balance.value

    order = {value: index for index, (value, _label) in enumerate(ContractManagementCategory.choices)}
    rows = tuple(
        PortfolioCategorySummary(
            category=category,
            label=labels.get(category, "Não classificado"),
            **values,
        )
        for category, values in sorted(
            grouped.items(), key=lambda item: (order.get(item[0], 999), item[0])
        )
    )
    return PortfolioSummary(
        categories=rows,
        contract_count=sum(row.contract_count for row in rows),
        current_value=sum((row.current_value for row in rows), zero),
        committed_budget=sum((row.committed_budget for row in rows), zero),
        paid_value=sum((row.paid_value for row in rows), zero),
        contract_balance=sum((row.contract_balance for row in rows), zero),
    )


def build_validity_progress(contract, *, today=None):
    today = today or date.today()
    total_days = (contract.validity_end - contract.validity_start).days + 1
    elapsed = min(max((today - contract.validity_start).days + 1, 0), max(total_days, 0))
    return ValidityProgress(
        total_days=total_days,
        elapsed_days=elapsed,
        remaining_days=max(total_days - elapsed, 0),
        percentage=_percentage(elapsed, total_days),
        has_started=today >= contract.validity_start,
        has_ended=today > contract.validity_end,
    )


def _add_months(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def build_monthly_evolution(contract, *, today=None, months=MONTHLY_EVOLUTION_MONTHS):
    """Executado (data da execução), faturado (emissão da NF) e pago (data do pagamento) por mês."""
    today = today or date.today()
    zero = Decimal("0")
    end = min(today, contract.validity_end)
    if end < contract.validity_start:
        return MonthlyEvolution((), zero, zero, zero, zero)
    first = _add_months(end.year, end.month, -(months - 1))
    if first < (contract.validity_start.year, contract.validity_start.month):
        first = (contract.validity_start.year, contract.validity_start.month)
    window_start = date(first[0], first[1], 1)
    following = _add_months(end.year, end.month, 1)
    window_end = date(following[0], following[1], 1) - timedelta(days=1)

    def totals(queryset, date_field, value_field):
        rows = (
            queryset.filter(**{f"{date_field}__gte": window_start, f"{date_field}__lte": window_end})
            .annotate(period=TruncMonth(date_field)).values("period").annotate(total=Sum(value_field))
        )
        return {(row["period"].year, row["period"].month): row["total"] or zero for row in rows}

    executed = totals(WorkOrderExecution.objects.filter(work_order__contract=contract),
                      "execution_date", "executed_value")
    invoiced = totals(contract.invoices.active(), "issue_date", "gross_value")
    paid = totals(Payment.objects.filter(invoice__contract=contract), "payment_date", "amount")

    entries, current = [], first
    while current <= (end.year, end.month):
        entries.append(MonthlyEntry(
            label=f"{current[1]:02d}/{current[0]}",
            executed=executed.get(current, zero), invoiced=invoiced.get(current, zero),
            paid=paid.get(current, zero),
        ))
        current = _add_months(current[0], current[1], 1)
    values = [v for e in entries for v in (e.executed, e.invoiced, e.paid)]
    return MonthlyEvolution(
        entries=tuple(entries), max_value=max(values, default=zero),
        total_executed=sum((e.executed for e in entries), zero),
        total_invoiced=sum((e.invoiced for e in entries), zero),
        total_paid=sum((e.paid for e in entries), zero),
    )


def build_executive_summary(contract, dashboard, *, today=None):
    today = today or date.today()
    fp = dashboard.financial_position
    current_value = contract.current_value
    financial_progress = tuple(
        ProgressRow(label, value, _percentage(value, current_value), tone)
        for label, value, tone in (
            ("Comprometido em OS", fp.committed_value.value, "reserved"),
            ("Executado", fp.executed_value.value, "executed"),
            ("Faturado", fp.invoiced_gross_value.value, "invoiced"),
            ("Pago", fp.paid_value.value, "paid"),
        )
    )
    work_orders = tuple(contract.work_orders.select_related("item").all())
    total = len(work_orders)
    status_rows = tuple(
        StatusRow(entry.label, entry.count, _percentage(entry.count, total))
        for entry in dashboard.work_order_statuses
    )
    period = period_for_date(calendar_year_periods(contract), today)
    open_hour = [wo for wo in work_orders if wo.status in OPEN_STATUSES and wo.hours is not None]
    delivered = [
        wo for wo in work_orders
        if wo.status == WorkOrderStatus.COMPLETED and wo.hours is not None
        and (period is None or (wo.completion_date and period.start_date <= wo.completion_date <= period.end_date))
    ]
    hours = HourSummary(
        open_hours=sum((wo.hours for wo in open_hour), Decimal("0")),
        delivered_period=period,
        delivered_hours=sum((wo.hours for wo in delivered), Decimal("0")),
        delivered_count=len(delivered),
        spent_hours=sum((wo.spent_hours for wo in delivered if wo.spent_hours is not None), Decimal("0")),
        with_spent_count=sum(1 for wo in delivered if wo.spent_hours is not None),
    )
    overdue_ids = {wo.pk for wo in dashboard.overdue_work_orders}
    open_rows = tuple(sorted(
        dashboard.open_work_orders,
        key=lambda wo: (wo.pk not in overdue_ids, wo.deadline or date.max, wo.pk),
    ))
    commitments = tuple(contract.commitments.all())
    return ExecutiveSummary(
        financial_progress=financial_progress,
        status_rows=status_rows,
        work_order_count=total,
        open_count=len(dashboard.open_work_orders),
        completed_count=sum(1 for wo in work_orders if wo.status == WorkOrderStatus.COMPLETED),
        commitment_count=len(commitments),
        active_commitment_count=sum(1 for c in commitments if getattr(c, "is_active", True)),
        has_hour_items=contract.items.filter(unit=ContractItemUnit.HOUR).exists(),
        hours=hours,
        open_rows=open_rows,
    )
