import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .periods import annual_context


CSV_HEADERS = (
    "tipo_registro",
    "indicador",
    "contrato",
    "processo",
    "identificador",
    "data",
    "fechamento_ano_civil",
    "ano_contratual",
    "competencia",
    "status",
    "item",
    "empenho",
    "ordem_servico",
    "nota_fiscal",
    "quantidade",
    "unidade",
    "valor_brl",
    "resultado_conferencia",
    "descricao",
)


@dataclass(frozen=True)
class ContractCsv:
    content: bytes
    row_count: int


def _safe_text(value):
    text = "" if value is None else str(value).replace("\x00", "")
    stripped = text.lstrip()
    if stripped and stripped[0] in "=+-@\t\r":
        return "'" + text
    return text


def _date(value):
    return value.strftime("%d/%m/%Y") if isinstance(value, date) else ""


def _decimal(value, places=2):
    if value in (None, ""):
        return ""
    quantizer = Decimal("1").scaleb(-places)
    return format(
        Decimal(value).quantize(quantizer, rounding=ROUND_HALF_UP), "f"
    ).replace(".", ",")


def _row(contract, *, record_type, indicator="", identifier="", record_date=None,
         competence="", status="", item="", commitment="", work_order="",
         invoice="", quantity="", unit="", value="", check_result="",
         description=""):
    periods = annual_context(contract, record_date) if record_date else {}
    return (
        record_type,
        indicator,
        contract.number,
        contract.process_number,
        identifier,
        _date(record_date),
        periods.get("calendar").label if periods.get("calendar") else "",
        periods.get("contract").label if periods.get("contract") else "",
        competence,
        status,
        item,
        commitment,
        work_order,
        invoice,
        _decimal(quantity, 4) if quantity != "" else "",
        unit,
        _decimal(value, 2) if value != "" else "",
        check_result,
        description,
    )


def build_contract_csv(report):
    """Serialize the same filtered report layer used by the web report."""
    contract = report.contract
    position = report.financial_position
    rows = [
        _row(contract, record_type="RESUMO", indicator="Contratado atual", value=contract.current_value),
        _row(contract, record_type="RESUMO", indicator="Empenhado ativo", value=position.total_committed_budget.value),
        _row(contract, record_type="RESUMO", indicator="Comprometido", value=position.committed_value.value),
        _row(contract, record_type="RESUMO", indicator="Executado", value=position.executed_value.value),
        _row(contract, record_type="RESUMO", indicator="Faturado bruto", value=position.invoiced_gross_value.value),
        _row(contract, record_type="RESUMO", indicator="Pago registrado", value=position.paid_value.value),
        _row(contract, record_type="RESUMO", indicator="Saldo contratual", value=position.contract_balance.value),
    ]
    rows.extend(
        _row(
            contract, record_type="EMPENHO", identifier=item.number,
            record_date=item.commitment_date, status="Ativo" if item.is_active else "Inativo",
            commitment=item.number, value=item.current_value, description=item.source,
        )
        for item in report.commitments
    )
    rows.extend(
        _row(
            contract,
            record_type="MOVIMENTO_EMPENHO",
            identifier=f"MOV-{movement.pk}",
            record_date=movement.movement_date,
            status=movement.get_movement_type_display(),
            commitment=commitment.number,
            value=movement.amount,
            description=(
                f"Documento oficial: {movement.document_reference}"
                if movement.document_reference
                else movement.notes
            ),
        )
        for commitment in report.commitments
        for movement in commitment.movements.all()
    )
    rows.extend(
        _row(
            contract, record_type="ORDEM_SERVICO", identifier=item.number,
            record_date=item.opening_date, status=item.get_status_display(),
            item=item.item.number, work_order=item.number, quantity=item.measure,
            unit=item.unit_name, value=item.total_value, description=item.description,
        )
        for item in report.work_orders
    )
    rows.extend(
        _row(
            contract, record_type="EXECUCAO", identifier=f"EXEC-{item.pk}",
            record_date=item.execution_date, competence=item.competence,
            item=item.work_order.item.number, work_order=item.work_order.number,
            quantity=item.executed_quantity, unit=item.work_order.unit_name,
            value=item.executed_value, description=item.notes,
        )
        for item in report.executions
    )
    invoice_checks = {item.pk: check for item, check in report.invoice_checks}
    rows.extend(
        _row(
            contract, record_type="NOTA_FISCAL",
            identifier=f"{item.number}/{item.series}", record_date=item.issue_date,
            competence=item.competence, status=item.status,
            item=item.item.number if item.item_id else item.work_order.item.number,
            commitment=item.allocation.commitment.number if item.allocation_id else "",
            work_order=item.work_order.number, invoice=f"{item.number}/{item.series}",
            value=item.gross_value,
            check_result=invoice_checks[item.pk].overall_status,
            description=item.notes,
        )
        for item in report.invoices
    )
    rows.extend(
        _row(
            contract, record_type="PAGAMENTO", identifier=f"PAG-{item.pk}",
            record_date=item.payment_date, competence=item.competence,
            status=item.status, work_order=item.invoice.work_order.number,
            invoice=f"{item.invoice.number}/{item.invoice.series}",
            value=item.amount, description=item.notes,
        )
        for item in report.payments
    )

    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_HEADERS)
    writer.writerows(tuple(_safe_text(value) for value in row) for row in rows)
    return ContractCsv(
        content=("\ufeff" + output.getvalue()).encode("utf-8"),
        row_count=len(rows),
    )


def filters_for_audit(filters):
    result = {}
    for key, value in filters.items():
        if value in (None, ""):
            continue
        if hasattr(value, "pk"):
            result[key] = value.pk
        elif isinstance(value, date):
            result[key] = value.isoformat()
        else:
            result[key] = str(value)
    return result
