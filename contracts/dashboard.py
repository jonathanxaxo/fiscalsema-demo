from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .invoice_checks import OverallStatus
from .models import ContractItemUnit, WorkOrderAllocationStatus, WorkOrderStatus
from .periods import calendar_year_periods, contract_year_periods, period_for_date
from .work_order_deadlines import FACTORY_NOTICE_DAYS
from .services import (
    commitment_financial_position,
    contract_financial_position,
    invoice_check_report,
    item_financial_position,
)


LOW_BALANCE_PERCENT = Decimal("20.00")
FINANCE_SUBMISSION_DAYS = 10
OPEN_WORK_ORDER_STATUSES = (
    WorkOrderStatus.OPEN,
    WorkOrderStatus.SIGNED,
    WorkOrderStatus.IN_PROGRESS,
    WorkOrderStatus.SUSPENDED,
)


INVOICE_ATTENTION_LABELS = {
    OverallStatus.PENDING: "Pendente de conferência",
    OverallStatus.DIVERGENCE: "Com divergência",
    OverallStatus.POSSIBLE_DUPLICATE: "Possível duplicidade",
    OverallStatus.BLOCKED: "Bloqueada",
}


@dataclass(frozen=True)
class InvoiceAttention:
    invoice: object
    status: str

    @property
    def status_label(self):
        return INVOICE_ATTENTION_LABELS.get(self.status, self.status)


@dataclass(frozen=True)
class CommitmentBalanceAlert:
    commitment: object
    available: Decimal
    percentage: Decimal


@dataclass(frozen=True)
class HourBalanceAlert:
    item: object
    available: Decimal
    percentage: Decimal


@dataclass(frozen=True)
class ItemPositionSummary:
    item: object
    position: object
    used_percentage: Decimal | None


@dataclass(frozen=True)
class CommitmentPositionSummary:
    commitment: object
    position: object
    used_percentage: Decimal | None


@dataclass(frozen=True)
class WorkOrderStatusSummary:
    value: str
    label: str
    count: int


@dataclass(frozen=True)
class InvoiceFinancialDeadline:
    invoice: object
    deadline: date
    is_overdue: bool


@dataclass(frozen=True)
class AnnualActivitySummary:
    period: object
    is_current: bool
    work_order_count: int
    work_order_value: Decimal
    executed_value: Decimal
    invoiced_value: Decimal
    paid_value: Decimal


@dataclass(frozen=True)
class AnnualItemLimitSummary:
    item: object
    period: object
    limit: Decimal
    ordered: Decimal
    executed: Decimal
    available: Decimal


@dataclass(frozen=True)
class MonthlyWorkOrderAttention:
    work_order: object
    competence: str
    state: str
    tone: str
    source: str


def work_order_requires_monthly_follow_up(work_order):
    return work_order.monthly_follow_up or work_order.item.unit == ContractItemUnit.MONTH


def _monthly_work_order_attentions(work_orders, *, today):
    """Situação da competência do mês atual das OS com acompanhamento mensal.

    Regra trazida do sistema principal (Sprint 19). Somente leitura: o aviso não
    autoriza pagamento nem substitui Atesto, RAER ou Termo de Homologação.
    """
    competence = f"{today.month:02d}/{today.year}"
    attentions = []
    for work_order in work_orders:
        if (
            not work_order_requires_monthly_follow_up(work_order)
            or work_order.status not in OPEN_WORK_ORDER_STATUSES
        ):
            continue
        executions = [e for e in work_order.executions.all() if e.competence == competence]
        invoices = [i for i in work_order.invoices.all() if i.competence == competence and i.returned_at is None]
        payments = [
            payment
            for invoice in invoices
            for payment in invoice.payments.all()
            if payment.competence == competence
        ]
        if work_order.status == WorkOrderStatus.SUSPENDED:
            state, tone = "OS suspensa; conferir providência e vigência", "warning"
        elif payments:
            state, tone = "Pagamento registrado para a competência", "success"
        elif invoices:
            state, tone = (
                "NF cadastrada; conferir Atesto, RAER, homologação e pagamento",
                "warning",
            )
        elif executions:
            state, tone = "Execução atualizada; aguardando NF e conferência documental", "warning"
        else:
            state, tone = "Atualização da competência pendente", "danger"
        attentions.append(
            MonthlyWorkOrderAttention(
                work_order=work_order,
                competence=competence,
                state=state,
                tone=tone,
                source=(
                    "marcação explícita da OS"
                    if work_order.monthly_follow_up
                    else "unidade contratual Mês"
                ),
            )
        )
    return tuple(attentions)


@dataclass(frozen=True)
class FactoryDeadlineAlert:
    """Cobrança da fábrica: prazo da fábrica em até 7 dias ou vencido (Sprint 36)."""

    work_order: object
    deadline: date
    days: int
    is_overdue: bool


@dataclass(frozen=True)
class DashboardSnapshot:
    contract: object
    financial_position: object
    has_operational_data: bool
    open_work_orders: tuple
    overdue_work_orders: tuple
    upcoming_work_orders: tuple
    pending_invoices: tuple[InvoiceAttention, ...]
    divergent_invoices: tuple[InvoiceAttention, ...]
    low_commitments: tuple[CommitmentBalanceAlert, ...]
    low_hour_items: tuple[HourBalanceAlert, ...]
    item_positions: tuple[ItemPositionSummary, ...]
    commitment_positions: tuple[CommitmentPositionSummary, ...]
    work_order_statuses: tuple[WorkOrderStatusSummary, ...]
    work_orders_without_allocation: tuple
    completed_work_orders_without_invoice: tuple
    invoice_financial_deadlines: tuple[InvoiceFinancialDeadline, ...]
    item_total: Decimal
    active_item_count: int
    inactive_item_count: int
    invoice_count: int
    payment_count: int
    finance_submission_days: int
    contract_balance_percentage: Decimal | None
    contract_balance_is_low: bool
    contract_is_expired: bool
    closing_rule: str
    calendar_periods: tuple[AnnualActivitySummary, ...]
    contract_years: tuple[AnnualActivitySummary, ...]
    annual_item_limits: tuple[AnnualItemLimitSummary, ...]
    current_calendar_period: object | None
    current_contract_year: object | None
    monthly_work_order_attentions: tuple[MonthlyWorkOrderAttention, ...] = ()
    factory_deadline_alerts: tuple[FactoryDeadlineAlert, ...] = ()
    # Sprint 39: faturamento dos serviços do catálogo
    accepted_without_homologation: tuple = ()
    homologated_without_invoice: tuple = ()
    returned_awaiting_correction: tuple = ()
    dimensioned_divergences: tuple = ()

    @property
    def attention_count(self):
        """Quantidade de pendências exibidas na lista "Precisa da sua atenção"."""
        return (
            int(self.contract_is_expired)
            + int(self.contract_balance_is_low)
            + len(self.overdue_work_orders)
            + len(self.factory_deadline_alerts)
            + len(self.low_commitments)
            + len(self.low_hour_items)
            + len(self.work_orders_without_allocation)
            + len(self.completed_work_orders_without_invoice)
            + len(self.pending_invoices)
            + len(self.divergent_invoices)
        )


def _percentage(available, total):
    if total <= Decimal("0.00"):
        return None
    return (available / total * Decimal("100.00")).quantize(Decimal("0.01"))


def _activity_summaries(periods, *, today, work_orders, executions, invoices):
    payments = tuple(
        payment for invoice in invoices for payment in invoice.payments.all()
    )
    return tuple(
        AnnualActivitySummary(
            period=period,
            is_current=period.contains(today),
            work_order_count=sum(
                1
                for item in work_orders
                if item.status != WorkOrderStatus.CANCELED
                and period.contains(item.opening_date)
            ),
            work_order_value=sum(
                (
                    item.total_value
                    for item in work_orders
                    if item.status != WorkOrderStatus.CANCELED
                    and period.contains(item.opening_date)
                ),
                Decimal("0.00"),
            ),
            executed_value=sum(
                (
                    item.executed_value
                    for item in executions
                    if period.contains(item.execution_date)
                ),
                Decimal("0.00"),
            ),
            invoiced_value=sum(
                (
                    item.gross_value
                    for item in invoices
                    if period.contains(item.issue_date)
                ),
                Decimal("0.00"),
            ),
            paid_value=sum(
                (
                    item.amount
                    for item in payments
                    if period.contains(item.payment_date)
                ),
                Decimal("0.00"),
            ),
        )
        for period in periods
    )


def build_contract_dashboard(contract, *, today=None):
    today = today or date.today()
    financial = contract_financial_position(contract)

    work_orders = tuple(
        contract.work_orders.select_related("item").prefetch_related(
            "allocations", "invoices__payments", "executions"
        )
    )
    open_work_orders = tuple(
        work_order
        for work_order in work_orders
        if work_order.status in OPEN_WORK_ORDER_STATUSES
    )
    overdue_work_orders = tuple(
        work_order
        for work_order in open_work_orders
        if work_order.deadline and work_order.deadline < today
    )
    upcoming_work_orders = tuple(
        sorted(
            (
                work_order
                for work_order in open_work_orders
                if work_order.deadline and work_order.deadline >= today
            ),
            key=lambda work_order: (work_order.deadline, work_order.pk),
        )
    )
    factory_deadline_alerts = tuple(sorted(
        (
            FactoryDeadlineAlert(
                work_order=work_order, deadline=work_order.factory_deadline,
                days=(work_order.factory_deadline - today).days,
                is_overdue=work_order.factory_deadline < today,
            )
            for work_order in open_work_orders
            if work_order.factory_deadline
            and (work_order.factory_deadline - today).days <= FACTORY_NOTICE_DAYS
            # OS já em atraso pelo prazo contratual tem o aviso de atraso, mais grave.
            and not (work_order.deadline and work_order.deadline < today)
        ),
        key=lambda alert: (alert.deadline, alert.work_order.pk),
    ))

    pending_invoices = []
    divergent_invoices = []
    invoices = tuple(contract.invoices.active().select_related(
        "contract", "work_order", "work_order__item", "item", "allocation"
    ).prefetch_related("payments"))
    executions = tuple(
        execution
        for work_order in work_orders
        for execution in work_order.executions.all()
    )
    for invoice in invoices:
        status = invoice_check_report(invoice).overall_status
        attention = InvoiceAttention(invoice=invoice, status=status)
        if status == OverallStatus.PENDING:
            pending_invoices.append(attention)
        elif status in {
            OverallStatus.DIVERGENCE,
            OverallStatus.POSSIBLE_DUPLICATE,
            OverallStatus.BLOCKED,
        }:
            divergent_invoices.append(attention)

    low_commitments = []
    active_commitments = tuple(
        contract.commitments.filter(is_active=True).prefetch_related(
            "movements", "allocations", "allocations__work_order"
        )
    )
    commitment_positions = []
    for commitment in active_commitments:
        position = commitment_financial_position(commitment)
        percentage = _percentage(
            position.available_balance.value, position.current_value.value
        )
        commitment_positions.append(
            CommitmentPositionSummary(
                commitment=commitment,
                position=position,
                used_percentage=(
                    None if percentage is None else Decimal("100.00") - percentage
                ),
            )
        )
        if percentage is not None and percentage < LOW_BALANCE_PERCENT:
            low_commitments.append(
                CommitmentBalanceAlert(
                    commitment=commitment,
                    available=position.available_balance.value,
                    percentage=percentage,
                )
            )

    low_hour_items = []
    items = tuple(contract.items.all())
    item_positions = []
    for item in items:
        position = item_financial_position(item)
        balance_percentage = _percentage(
            position.quantity_balance.value, item.contracted_quantity
        )
        item_positions.append(
            ItemPositionSummary(
                item=item,
                position=position,
                used_percentage=(
                    None
                    if balance_percentage is None
                    else Decimal("100.00") - balance_percentage
                ),
            )
        )
        if (
            item.is_active
            and item.unit == ContractItemUnit.HOUR
            and balance_percentage is not None
            and balance_percentage < LOW_BALANCE_PERCENT
        ):
            low_hour_items.append(
                HourBalanceAlert(
                    item=item,
                    available=position.quantity_balance.value,
                    percentage=balance_percentage,
                )
            )

    work_order_statuses = tuple(
        WorkOrderStatusSummary(
            value=value,
            label=label,
            count=sum(1 for work_order in work_orders if work_order.status == value),
        )
        for value, label in WorkOrderStatus.choices
        if any(work_order.status == value for work_order in work_orders)
    )
    financially_effective_statuses = {
        WorkOrderStatus.SIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.COMPLETED,
    }
    work_orders_without_allocation = tuple(
        work_order
        for work_order in work_orders
        if work_order.status in financially_effective_statuses
        and not any(
            allocation.status == WorkOrderAllocationStatus.ACTIVE
            for allocation in work_order.allocations.all()
        )
    )
    completed_work_orders_without_invoice = tuple(
        work_order
        for work_order in work_orders
        if work_order.status == WorkOrderStatus.COMPLETED
        and not work_order.invoices.active().exists()
    )
    invoice_financial_deadlines = tuple(
        InvoiceFinancialDeadline(
            invoice=invoice,
            deadline=invoice.issue_date + timedelta(days=FINANCE_SUBMISSION_DAYS),
            is_overdue=(
                invoice.issue_date + timedelta(days=FINANCE_SUBMISSION_DAYS)
            ) < today,
        )
        for invoice in sorted(invoices, key=lambda entry: (entry.issue_date, entry.pk))
    )

    contract_percentage = _percentage(
        financial.contract_balance.value, contract.current_value
    )
    has_operational_data = any(
        (
            bool(active_commitments),
            bool(work_orders),
            bool(invoices),
        )
    )
    calendar_periods = calendar_year_periods(contract)
    contract_periods = contract_year_periods(contract)
    annual_item_limits = tuple(
        AnnualItemLimitSummary(
            item=item,
            period=period,
            limit=item.annual_operational_limit,
            ordered=sum(
                (
                    work_order.measure
                    for work_order in work_orders
                    if work_order.item_id == item.pk
                    and work_order.status not in {
                        WorkOrderStatus.DRAFT,
                        WorkOrderStatus.CANCELED,
                    }
                    and period.contains(work_order.opening_date)
                ),
                Decimal("0"),
            ),
            executed=sum(
                (
                    execution.executed_quantity
                    for execution in executions
                    if execution.work_order.item_id == item.pk
                    and period.contains(execution.execution_date)
                ),
                Decimal("0"),
            ),
            available=max(
                Decimal("0"),
                item.annual_operational_limit
                - sum(
                    (
                        work_order.measure
                        for work_order in work_orders
                        if work_order.item_id == item.pk
                        and work_order.status not in {
                            WorkOrderStatus.DRAFT,
                            WorkOrderStatus.CANCELED,
                        }
                        and period.contains(work_order.opening_date)
                    ),
                    Decimal("0"),
                ),
            ),
        )
        for item in items
        if item.annual_operational_limit is not None
        for period in contract_periods
    )
    billing = _service_billing(contract)
    return DashboardSnapshot(
        accepted_without_homologation=billing["accepted"],
        homologated_without_invoice=billing["homologated"],
        returned_awaiting_correction=billing["returned"],
        dimensioned_divergences=billing["divergent"],
        contract=contract,
        financial_position=financial,
        has_operational_data=has_operational_data,
        open_work_orders=open_work_orders,
        overdue_work_orders=overdue_work_orders,
        factory_deadline_alerts=factory_deadline_alerts,
        upcoming_work_orders=upcoming_work_orders,
        pending_invoices=tuple(pending_invoices),
        divergent_invoices=tuple(divergent_invoices),
        low_commitments=tuple(low_commitments),
        low_hour_items=tuple(low_hour_items),
        item_positions=tuple(item_positions),
        commitment_positions=tuple(commitment_positions),
        work_order_statuses=work_order_statuses,
        work_orders_without_allocation=work_orders_without_allocation,
        completed_work_orders_without_invoice=completed_work_orders_without_invoice,
        invoice_financial_deadlines=invoice_financial_deadlines,
        item_total=sum(
            (entry.position.total_value.value for entry in item_positions),
            Decimal("0.00"),
        ),
        active_item_count=sum(1 for item in items if item.is_active),
        inactive_item_count=sum(1 for item in items if not item.is_active),
        invoice_count=len(invoices),
        payment_count=sum(len(invoice.payments.all()) for invoice in invoices),
        finance_submission_days=FINANCE_SUBMISSION_DAYS,
        contract_balance_percentage=contract_percentage,
        contract_balance_is_low=(
            contract_percentage is not None
            and contract_percentage < LOW_BALANCE_PERCENT
        ),
        contract_is_expired=contract.current_validity_end < today,
        closing_rule="ANO CIVIL — fechamento oficial em 31 de dezembro",
        calendar_periods=_activity_summaries(
            calendar_periods,
            today=today,
            work_orders=work_orders,
            executions=executions,
            invoices=invoices,
        ),
        contract_years=_activity_summaries(
            contract_periods,
            today=today,
            work_orders=work_orders,
            executions=executions,
            invoices=invoices,
        ),
        annual_item_limits=annual_item_limits,
        current_calendar_period=period_for_date(calendar_periods, today),
        current_contract_year=period_for_date(contract_periods, today),
        monthly_work_order_attentions=_monthly_work_order_attentions(work_orders, today=today),
    )


def _service_billing(contract):
    """Avisos de faturamento dos serviços do catálogo (Sprint 39; referência: FiscalSema Light)."""
    from .models import ServiceLineStatus, WorkOrderServiceLine

    lines = tuple(
        WorkOrderServiceLine.objects.filter(work_order__contract=contract)
        .exclude(work_order__status=WorkOrderStatus.CANCELED)
        .select_related("work_order").prefetch_related("invoices")
    )

    def grouped(predicate):
        counts = {}
        for line in lines:
            if predicate(line):
                counts.setdefault(line.work_order, 0)
                counts[line.work_order] += 1
        return tuple(sorted(counts.items(), key=lambda pair: pair[0].pk))

    invoices = tuple(contract.invoices.select_related("work_order").prefetch_related("replaced_by", "service_lines"))
    return {
        "accepted": grouped(lambda line: line.delivery_status == ServiceLineStatus.ACCEPTED),
        "homologated": grouped(lambda line: line.delivery_status == ServiceLineStatus.HOMOLOGATED
                               and line.active_invoice is None),
        "returned": tuple(
            invoice for invoice in invoices
            if invoice.is_returned and not any(other.returned_at is None for other in invoice.replaced_by.all())
        ),
        "divergent": tuple(
            invoice for invoice in invoices if not invoice.is_returned and invoice.dimensioned_difference
        ),
    }
