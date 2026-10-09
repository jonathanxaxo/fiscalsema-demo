from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from .models import WorkOrderAllocationStatus, WorkOrderStatus


class CheckStatus:
    OK = "OK"
    NOT_APPLICABLE = "NAO_APLICAVEL"
    PENDING = "COM_PENDENCIA"
    DIVERGENCE = "COM_DIVERGENCIA"
    POSSIBLE_DUPLICATE = "POSSIVEL_DUPLICIDADE"
    BLOCKED = "BLOQUEADA"


class OverallStatus:
    CONFERRED = "CONFERIDA"
    PENDING = "COM_PENDENCIA"
    DIVERGENCE = "COM_DIVERGENCIA"
    POSSIBLE_DUPLICATE = "POSSIVEL_DUPLICIDADE"
    BLOCKED = "BLOQUEADA"


@dataclass(frozen=True)
class InvoiceCheckResult:
    code: str
    label: str
    status: str
    message: str
    expected: str = ""
    actual: str = ""
    difference: str = ""
    related_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class InvoiceCheckReport:
    overall_status: str
    checks: tuple[InvoiceCheckResult, ...]


def _money(value):
    value = Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    sign = "-" if value < 0 else ""
    integer, decimal = f"{abs(value):.2f}".split(".")
    groups = []
    while integer:
        groups.append(integer[-3:])
        integer = integer[:-3]
    return f"{sign}R$ {'.'.join(reversed(groups))},{decimal}"


def _overall_status(checks):
    statuses = {check.status for check in checks}
    for status in (
        OverallStatus.BLOCKED,
        OverallStatus.POSSIBLE_DUPLICATE,
        OverallStatus.DIVERGENCE,
        OverallStatus.PENDING,
    ):
        if status in statuses:
            return status
    return OverallStatus.CONFERRED


def evaluate_invoice(
    *, invoice, other_invoice_total, possible_duplicate_ids=(),
    has_active_allocations=False,
):
    checks = []
    contract_matches = invoice.work_order.contract_id == invoice.contract_id
    checks.append(InvoiceCheckResult(
        code="CONTRATO", label="Contrato",
        status=CheckStatus.OK if contract_matches else CheckStatus.BLOCKED,
        message=("A NF e a OS pertencem ao mesmo contrato." if contract_matches
                 else "A NF e a OS pertencem a contratos diferentes."),
        expected=invoice.work_order.contract.number, actual=invoice.contract.number,
    ))

    supplier_matches = invoice.supplier_name.casefold() == invoice.contract.supplier_name.casefold()
    checks.append(InvoiceCheckResult(
        code="FORNECEDOR", label="Fornecedor",
        status=CheckStatus.OK if supplier_matches else CheckStatus.DIVERGENCE,
        message=("O fornecedor corresponde ao contrato." if supplier_matches
                 else "O fornecedor informado diverge do contrato."),
        expected=invoice.contract.supplier_name, actual=invoice.supplier_name,
    ))

    tax_id_matches = invoice.supplier_tax_id == invoice.contract.supplier_tax_id
    checks.append(InvoiceCheckResult(
        code="CNPJ_CPF", label="CNPJ/CPF",
        status=CheckStatus.OK if tax_id_matches else CheckStatus.DIVERGENCE,
        message=("O documento fiscal corresponde ao contrato." if tax_id_matches
                 else "O documento fiscal diverge do contrato."),
        expected=invoice.contract.supplier_tax_id, actual=invoice.supplier_tax_id,
    ))

    if not contract_matches or invoice.work_order.status == WorkOrderStatus.CANCELED:
        order_status = CheckStatus.BLOCKED
        order_message = ("A OS está cancelada e impede a conferência."
                         if invoice.work_order.status == WorkOrderStatus.CANCELED
                         else "A OS não pertence ao contrato da NF.")
    else:
        order_status = CheckStatus.OK
        order_message = "A OS está vinculada ao contrato e não está cancelada."
    checks.append(InvoiceCheckResult(
        code="ORDEM_SERVICO", label="Ordem de Serviço", status=order_status,
        message=order_message,
        expected=f"OS do contrato {invoice.contract.number}, não cancelada",
        actual=f"{invoice.work_order.number} — {invoice.work_order.get_status_display()}",
    ))

    if invoice.item_id is None:
        item_status, item_message, item_actual = (
            CheckStatus.PENDING, "O item da OS não foi informado na NF.", "Não informado"
        )
    elif invoice.item_id != invoice.work_order.item_id:
        item_status, item_message, item_actual = (
            CheckStatus.DIVERGENCE, "O item informado diverge do item da OS.", invoice.item.number
        )
    else:
        item_status, item_message, item_actual = (
            CheckStatus.OK, "O item corresponde ao item da OS.", invoice.item.number
        )
    checks.append(InvoiceCheckResult(
        code="ITEM", label="Item", status=item_status, message=item_message,
        expected=invoice.work_order.item.number, actual=item_actual,
    ))

    values_valid = (
        invoice.gross_value > Decimal("0.00")
        and Decimal("0.00") <= invoice.deduction_value <= invoice.gross_value
        and Decimal("0.00") <= invoice.accepted_value <= invoice.gross_value
    )
    checks.append(InvoiceCheckResult(
        code="VALOR", label="Valores da NF",
        status=CheckStatus.OK if values_valid else CheckStatus.BLOCKED,
        message=("Os valores respeitam os limites objetivos; nenhuma fórmula de aceite foi inferida."
                 if values_valid else "A NF possui valor matematicamente inválido."),
        expected="Bruto > zero; glosa e aceito entre zero e o bruto",
        actual=(f"Bruto {_money(invoice.gross_value)}; glosa {_money(invoice.deduction_value)}; "
                f"aceito {_money(invoice.accepted_value)}"),
    ))

    cumulative = other_invoice_total + invoice.gross_value
    balance = invoice.work_order.total_value - cumulative
    checks.append(InvoiceCheckResult(
        code="SALDO_FATURAVEL", label="Saldo faturável",
        status=CheckStatus.OK if balance >= Decimal("0.00") else CheckStatus.BLOCKED,
        message=("O total bruto acumulado permanece dentro do valor da OS."
                 if balance >= Decimal("0.00") else "O total bruto acumulado ultrapassa o valor da OS."),
        expected=_money(invoice.work_order.total_value), actual=_money(cumulative),
        difference=_money(balance),
    ))

    if invoice.allocation_id:
        allocation_matches = (
            invoice.allocation.work_order_id == invoice.work_order_id
            and invoice.allocation.work_order.contract_id == invoice.contract_id
        )
        if not allocation_matches:
            allocation_status, allocation_message = (
                CheckStatus.BLOCKED, "O rateio informado não pertence à mesma OS e contrato."
            )
        elif invoice.allocation.status != WorkOrderAllocationStatus.ACTIVE:
            allocation_status, allocation_message = (
                CheckStatus.DIVERGENCE, "O rateio informado não está ativo."
            )
        else:
            allocation_status, allocation_message = (
                CheckStatus.OK, "O rateio informado está ativo e pertence à mesma OS."
            )
        allocation_actual = str(invoice.allocation)
    elif has_active_allocations:
        allocation_status, allocation_message, allocation_actual = (
            CheckStatus.PENDING,
            "A OS possui rateio ativo, mas a NF não indica qual foi utilizado.",
            "Não informado",
        )
    else:
        allocation_status, allocation_message, allocation_actual = (
            CheckStatus.NOT_APPLICABLE,
            "A OS não possui rateio ativo para conferir nesta etapa.",
            "Não aplicável",
        )
    checks.append(InvoiceCheckResult(
        code="EMPENHO_RATEIO", label="Empenho/rateio", status=allocation_status,
        message=allocation_message, expected="Rateio ativo da mesma OS, quando aplicável",
        actual=allocation_actual,
    ))

    duplicate_ids = tuple(sorted(possible_duplicate_ids))
    checks.append(InvoiceCheckResult(
        code="DUPLICIDADE", label="Duplicidade",
        status=CheckStatus.POSSIBLE_DUPLICATE if duplicate_ids else CheckStatus.OK,
        message=("Há registro(s) com contexto fiscal ou hash coincidente; exige revisão humana."
                 if duplicate_ids else "Nenhuma possível duplicidade foi encontrada."),
        expected="Nenhuma coincidência contextual ou de hash",
        actual=(", ".join(f"NF #{identifier}" for identifier in duplicate_ids)
                if duplicate_ids else "Nenhuma"),
        related_ids=duplicate_ids,
    ))

    checks = tuple(checks)
    return InvoiceCheckReport(overall_status=_overall_status(checks), checks=checks)
