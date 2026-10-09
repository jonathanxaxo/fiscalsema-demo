from dataclasses import dataclass

from .models import Payment, WorkOrderExecution
from .periods import calendar_year_periods, contract_year_periods
from .services import contract_financial_position, invoice_check_report


@dataclass(frozen=True)
class AccountabilitySnapshot:
    contract: object
    financial_position: object
    commitments: tuple
    work_orders: tuple
    executions: tuple
    invoices: tuple
    payments: tuple
    invoice_checks: tuple
    has_filters: bool
    closing_rule: str
    calendar_periods: tuple
    contract_years: tuple


def _period(queryset, field, start_date, end_date):
    if start_date:
        queryset = queryset.filter(**{f"{field}__gte": start_date})
    if end_date:
        queryset = queryset.filter(**{f"{field}__lte": end_date})
    return queryset


def build_accountability_snapshot(contract, filters):
    """Build a read-only, traceable view without persisting inferred totals."""
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    competence = filters.get("competence")
    commitment = filters.get("commitment")
    work_order = filters.get("work_order")
    invoice = filters.get("invoice")

    commitments = contract.commitments.prefetch_related("movements")
    work_orders = contract.work_orders.select_related("item")
    executions = WorkOrderExecution.objects.filter(
        work_order__contract=contract
    ).select_related("work_order")
    invoices = contract.invoices.select_related("work_order", "allocation")
    payments = Payment.objects.filter(invoice__contract=contract).select_related(
        "invoice", "invoice__work_order"
    )

    commitments = _period(commitments, "commitment_date", start_date, end_date)
    work_orders = _period(work_orders, "opening_date", start_date, end_date)
    executions = _period(executions, "execution_date", start_date, end_date)
    invoices = _period(invoices, "issue_date", start_date, end_date)
    payments = _period(payments, "payment_date", start_date, end_date)

    if competence:
        executions = executions.filter(competence=competence)
        invoices = invoices.filter(competence=competence)
        payments = payments.filter(competence=competence)
    if commitment:
        work_orders = work_orders.filter(allocations__commitment=commitment)
        executions = executions.filter(work_order__allocations__commitment=commitment)
        invoices = invoices.filter(work_order__allocations__commitment=commitment)
        payments = payments.filter(
            invoice__work_order__allocations__commitment=commitment
        )
        commitments = commitments.filter(pk=commitment.pk)
    if work_order:
        work_orders = work_orders.filter(pk=work_order.pk)
        executions = executions.filter(work_order=work_order)
        invoices = invoices.filter(work_order=work_order)
        payments = payments.filter(invoice__work_order=work_order)
    if invoice:
        work_orders = work_orders.filter(pk=invoice.work_order_id)
        executions = executions.filter(work_order_id=invoice.work_order_id)
        invoices = invoices.filter(pk=invoice.pk)
        payments = payments.filter(invoice=invoice)
        if invoice.allocation_id:
            commitments = commitments.filter(pk=invoice.allocation.commitment_id)
        else:
            commitments = commitments.none()

    commitments = tuple(commitments.distinct())
    work_orders = tuple(work_orders.distinct())
    executions = tuple(executions.distinct())
    invoices = tuple(invoices.distinct())
    payments = tuple(payments.distinct())
    return AccountabilitySnapshot(
        contract=contract,
        financial_position=contract_financial_position(contract),
        commitments=commitments,
        work_orders=work_orders,
        executions=executions,
        invoices=invoices,
        payments=payments,
        invoice_checks=tuple(
            (invoice, invoice_check_report(invoice)) for invoice in invoices
        ),
        has_filters=any(filters.values()),
        closing_rule="ANO CIVIL — fechamento oficial em 31 de dezembro",
        calendar_periods=calendar_year_periods(contract),
        contract_years=contract_year_periods(contract),
    )
