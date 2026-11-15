from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP


MONEY_QUANTUM = Decimal("0.01")


def quantize_money(value):
    """Return a monetary Decimal rounded to Brazilian cent precision."""
    if not isinstance(value, Decimal):
        raise TypeError("Valores monetários devem usar Decimal.")
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class NegativeBalanceError(ValueError):
    pass


@dataclass(frozen=True)
class CalculationEvidence:
    source_type: str
    source_id: str
    description: str
    value: Decimal
    operation: str = "ADD"

    def __post_init__(self):
        if not all(
            isinstance(value, str)
            for value in (self.source_type, self.source_id, self.description, self.operation)
        ):
            raise TypeError("Os identificadores da evidência devem ser textos.")
        if not self.source_type.strip() or not self.source_id.strip() or not self.description.strip():
            raise ValueError("A evidência do cálculo precisa identificar sua origem.")
        if not isinstance(self.value, Decimal):
            raise TypeError("O valor da evidência deve usar Decimal.")
        if self.value < Decimal("0"):
            raise ValueError("A evidência de origem não pode possuir valor negativo.")
        if self.operation not in {"BASE", "ADD", "SUBTRACT", "MULTIPLY"}:
            raise ValueError("A operação da evidência do cálculo é inválida.")


@dataclass(frozen=True)
class CalculationResult:
    value: Decimal
    evidence: tuple[CalculationEvidence, ...]


@dataclass(frozen=True)
class ItemFinancialPosition:
    total_value: CalculationResult
    used_quantity: CalculationResult
    quantity_balance: CalculationResult
    used_value: CalculationResult
    financial_balance: CalculationResult


@dataclass(frozen=True)
class CommitmentFinancialPosition:
    current_value: CalculationResult
    committed_value: CalculationResult
    available_balance: CalculationResult


@dataclass(frozen=True)
class ContractFinancialPosition:
    total_committed_budget: CalculationResult
    committed_value: CalculationResult
    executed_value: CalculationResult
    invoiced_gross_value: CalculationResult
    paid_value: CalculationResult
    contract_balance: CalculationResult


@dataclass(frozen=True)
class InvoiceFinancialPosition:
    work_order_value: CalculationResult
    invoiced_gross_value: CalculationResult
    billable_balance: CalculationResult


@dataclass(frozen=True)
class PaymentFinancialPosition:
    provisional_payable_limit: CalculationResult
    paid_total: CalculationResult
    payment_balance: CalculationResult


def _require_decimal(**values):
    if not all(isinstance(value, Decimal) for value in values.values()):
        names = ", ".join(values)
        raise TypeError(f"Os valores {names} devem usar Decimal.")


def _require_nonnegative(**values):
    for name, value in values.items():
        if value < Decimal("0"):
            raise ValueError(f"O valor {name} não pode ser negativo.")


def _evidence_total(evidence):
    evidence = tuple(evidence)
    total = sum((component.value for component in evidence), Decimal("0"))
    return total, evidence


def _as_operation(evidence, operation):
    return tuple(replace(component, operation=operation) for component in evidence)


QUANTITY_QUANTUM = Decimal("0.0001")


def calculate_service_units(quantity, weight):
    """UST/HST/USN de um serviço do catálogo = quantidade × peso (Sprint 38; 4 casas)."""
    _require_decimal(quantity=quantity, weight=weight)
    return (quantity * weight).quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_item_total(quantity, unit_value):
    _require_decimal(quantity=quantity, unit_value=unit_value)
    return quantize_money(quantity * unit_value)


def calculate_commitment_current_value(initial_value, reinforcements, cancellations):
    _require_decimal(
        initial_value=initial_value,
        reinforcements=reinforcements,
        cancellations=cancellations,
    )
    return initial_value + reinforcements - cancellations


def calculate_item_financial_position(
    *,
    item_id,
    contracted_quantity,
    unit_value,
    used_quantity_evidence=(),
    used_value_evidence=(),
):
    _require_decimal(
        contracted_quantity=contracted_quantity,
        unit_value=unit_value,
    )
    _require_nonnegative(
        contracted_quantity=contracted_quantity,
        unit_value=unit_value,
    )
    used_quantity, quantity_evidence = _evidence_total(used_quantity_evidence)
    used_value, value_evidence = _evidence_total(used_value_evidence)
    total_value = calculate_item_total(contracted_quantity, unit_value)
    quantity_balance = contracted_quantity - used_quantity
    financial_balance = total_value - used_value
    if quantity_balance < Decimal("0"):
        raise NegativeBalanceError("A quantidade utilizada supera a contratada.")
    if financial_balance < Decimal("0"):
        raise NegativeBalanceError("O valor utilizado supera o valor total do item.")
    item_evidence = (
        CalculationEvidence(
            source_type="ITEM",
            source_id=str(item_id),
            description="Quantidade contratada",
            value=contracted_quantity,
            operation="MULTIPLY",
        ),
        CalculationEvidence(
            source_type="ITEM",
            source_id=str(item_id),
            description="Valor unitário",
            value=unit_value,
            operation="MULTIPLY",
        ),
    )
    return ItemFinancialPosition(
        total_value=CalculationResult(total_value, item_evidence),
        used_quantity=CalculationResult(used_quantity, quantity_evidence),
        quantity_balance=CalculationResult(
            quantity_balance,
            item_evidence[:1] + _as_operation(quantity_evidence, "SUBTRACT"),
        ),
        used_value=CalculationResult(used_value, value_evidence),
        financial_balance=CalculationResult(
            financial_balance,
            item_evidence + _as_operation(value_evidence, "SUBTRACT"),
        ),
    )


def calculate_commitment_financial_position(
    *,
    commitment_id,
    initial_value,
    reinforcement_evidence=(),
    cancellation_evidence=(),
    committed_evidence=(),
):
    _require_decimal(initial_value=initial_value)
    _require_nonnegative(initial_value=initial_value)
    reinforcements, reinforcements_detail = _evidence_total(reinforcement_evidence)
    cancellations, cancellations_detail = _evidence_total(cancellation_evidence)
    committed, committed_detail = _evidence_total(committed_evidence)
    current = calculate_commitment_current_value(
        initial_value,
        reinforcements,
        cancellations,
    )
    available = current - committed
    if current < Decimal("0"):
        raise NegativeBalanceError("O valor atual do empenho não pode ser negativo.")
    if available < Decimal("0"):
        raise NegativeBalanceError("O valor comprometido supera o valor atual do empenho.")
    initial_detail = (
        CalculationEvidence(
            source_type="EMPENHO",
            source_id=str(commitment_id),
            description="Valor inicial",
            value=initial_value,
            operation="BASE",
        ),
    )
    current_detail = (
        initial_detail
        + _as_operation(reinforcements_detail, "ADD")
        + _as_operation(cancellations_detail, "SUBTRACT")
    )
    return CommitmentFinancialPosition(
        current_value=CalculationResult(current, current_detail),
        committed_value=CalculationResult(committed, committed_detail),
        available_balance=CalculationResult(
            available,
            current_detail + _as_operation(committed_detail, "SUBTRACT"),
        ),
    )


def calculate_contract_financial_position(
    *,
    contract_id,
    current_value,
    commitment_evidence=(),
    committed_evidence=(),
    executed_evidence=(),
    invoiced_evidence=(),
    paid_evidence=(),
):
    _require_decimal(current_value=current_value)
    _require_nonnegative(current_value=current_value)
    total_committed_budget, commitment_detail = _evidence_total(commitment_evidence)
    committed, committed_detail = _evidence_total(committed_evidence)
    executed, executed_detail = _evidence_total(executed_evidence)
    invoiced, invoiced_detail = _evidence_total(invoiced_evidence)
    paid, paid_detail = _evidence_total(paid_evidence)
    balance = current_value - committed
    if balance < Decimal("0"):
        raise NegativeBalanceError("O valor comprometido supera o valor atual do contrato.")
    contract_detail = (
        CalculationEvidence(
            source_type="CONTRATO",
            source_id=str(contract_id),
            description="Valor atual do contrato",
            value=current_value,
            operation="BASE",
        ),
    )
    return ContractFinancialPosition(
        total_committed_budget=CalculationResult(
            total_committed_budget,
            commitment_detail,
        ),
        committed_value=CalculationResult(committed, committed_detail),
        executed_value=CalculationResult(executed, executed_detail),
        invoiced_gross_value=CalculationResult(invoiced, invoiced_detail),
        paid_value=CalculationResult(paid, paid_detail),
        contract_balance=CalculationResult(
            balance,
            contract_detail + _as_operation(committed_detail, "SUBTRACT"),
        ),
    )


def calculate_payment_financial_position(
    *, invoice_id, gross_value, accepted_value, payment_evidence=()
):
    _require_decimal(gross_value=gross_value, accepted_value=accepted_value)
    _require_nonnegative(gross_value=gross_value, accepted_value=accepted_value)
    provisional_limit = min(gross_value, accepted_value)
    paid, paid_detail = _evidence_total(payment_evidence)
    balance = provisional_limit - paid
    if balance < Decimal("0.00"):
        raise NegativeBalanceError(
            "O total pago supera o limite provisório conservador da Nota Fiscal."
        )
    limit_evidence = (
        CalculationEvidence(
            source_type="NOTA_FISCAL",
            source_id=str(invoice_id),
            description="Menor valor entre bruto e aceito informado",
            value=provisional_limit,
            operation="BASE",
        ),
    )
    return PaymentFinancialPosition(
        provisional_payable_limit=CalculationResult(provisional_limit, limit_evidence),
        paid_total=CalculationResult(paid, paid_detail),
        payment_balance=CalculationResult(
            balance, limit_evidence + _as_operation(paid_detail, "SUBTRACT")
        ),
    )


def calculate_invoice_financial_position(
    *, work_order_id, work_order_value, invoice_evidence=()
):
    _require_decimal(work_order_value=work_order_value)
    _require_nonnegative(work_order_value=work_order_value)
    invoiced, invoice_detail = _evidence_total(invoice_evidence)
    balance = work_order_value - invoiced
    if balance < Decimal("0"):
        raise NegativeBalanceError("O total bruto das Notas Fiscais supera o valor da OS.")
    order_detail = (
        CalculationEvidence(
            source_type="ORDEM_SERVICO",
            source_id=str(work_order_id),
            description="Valor total da OS",
            value=work_order_value,
            operation="BASE",
        ),
    )
    return InvoiceFinancialPosition(
        work_order_value=CalculationResult(work_order_value, order_detail),
        invoiced_gross_value=CalculationResult(invoiced, invoice_detail),
        billable_balance=CalculationResult(
            balance, order_detail + _as_operation(invoice_detail, "SUBTRACT")
        ),
    )
