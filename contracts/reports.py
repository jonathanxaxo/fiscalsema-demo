from dataclasses import dataclass

from .accountability import build_accountability_snapshot
from .forms import ReportFilterForm
from .services import invoice_check_report


@dataclass(frozen=True)
class ContractReport:
    contract: object
    financial_position: object
    section: str
    commitments: tuple
    work_orders: tuple
    executions: tuple
    invoices: tuple
    payments: tuple
    invoice_checks: tuple
    applied_status: str
    closing_rule: str
    calendar_periods: tuple
    contract_years: tuple


def build_contract_report(contract, filters):
    base = build_accountability_snapshot(contract, filters)
    section = filters.get("section") or ReportFilterForm.Section.ALL
    status = filters.get("status") or ""
    commitments = base.commitments
    work_orders = base.work_orders
    executions = base.executions
    invoices = base.invoices
    payments = base.payments

    if section == ReportFilterForm.Section.FINANCIAL:
        commitments = work_orders = executions = invoices = payments = ()
    elif section == ReportFilterForm.Section.OPERATIONAL:
        invoices = payments = ()
    elif section == ReportFilterForm.Section.BILLING:
        commitments = work_orders = executions = ()

    if status:
        kind, value = status.split(":", 1)
        if kind == "OS":
            work_orders = tuple(item for item in work_orders if item.status == value)
            work_order_ids = {item.pk for item in work_orders}
            executions = tuple(
                item for item in executions if item.work_order_id in work_order_ids
            )
            commitments = invoices = payments = ()
        elif kind == "NF":
            invoices = tuple(item for item in invoices if item.status == value)
            invoice_ids = {item.pk for item in invoices}
            payments = tuple(
                item for item in payments if item.invoice_id in invoice_ids
            )
            commitments = work_orders = executions = ()
        elif kind == "PAGAMENTO":
            payments = tuple(item for item in payments if item.status == value)
            invoice_ids = {item.invoice_id for item in payments}
            invoices = tuple(item for item in invoices if item.pk in invoice_ids)
            commitments = work_orders = executions = ()

    return ContractReport(
        contract=contract,
        financial_position=base.financial_position,
        section=section,
        commitments=commitments,
        work_orders=work_orders,
        executions=executions,
        invoices=invoices,
        payments=payments,
        invoice_checks=tuple(
            (invoice, invoice_check_report(invoice)) for invoice in invoices
        ),
        applied_status=status,
        closing_rule=base.closing_rule,
        calendar_periods=base.calendar_periods,
        contract_years=base.contract_years,
    )
