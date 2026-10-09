import csv
import hashlib
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import PermissionDenied, ValidationError
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openpyxl import load_workbook

from contracts.models import (
    BudgetCommitment,
    ContractItem,
    Invoice,
    WorkOrder,
    WorkOrderStatus,
)
from contracts.services import (
    contracts_writable_by,
    create_budget_commitment,
    create_invoice,
    create_work_order,
)

from .models import ImportEvent, SpreadsheetImport


MAX_UPLOAD_BYTES = settings.SPREADSHEET_MAX_UPLOAD_SIZE
MAX_ROWS = 500
MAX_COLUMNS = 80


def _field(name, label, *, required=True, aliases=()):
    return {
        "name": name,
        "label": label,
        "required": required,
        "aliases": {name.casefold(), label.casefold(), *(alias.casefold() for alias in aliases)},
    }


ENTITY_FIELDS = {
    SpreadsheetImport.EntityType.COMMITMENT: (
        _field("number", "Número do empenho", aliases=("empenho", "numero")),
        _field("ped", "PED"),
        _field("commitment_date", "Data do empenho", aliases=("data",)),
        _field("initial_value", "Valor inicial", aliases=("valor", "valor empenhado")),
        _field("source", "Fonte"),
        _field("notes", "Observação", required=False, aliases=("observacoes", "notas")),
        _field("is_active", "Ativo", required=False),
    ),
    SpreadsheetImport.EntityType.WORK_ORDER: (
        _field("number", "Número da OS", aliases=("os", "numero")),
        _field("item_number", "Número do item", aliases=("item",)),
        _field("description", "Descrição", aliases=("objeto",)),
        _field("quantity", "Quantidade", required=False),
        _field("hours", "Horas", required=False, aliases=("hst",)),
        _field("responsible", "Responsável"),
        _field("opening_date", "Data de abertura", aliases=("data",)),
        _field("signature_date", "Data de assinatura", required=False),
        _field("start_date", "Data de início", required=False, aliases=("inicio",)),
        _field("deadline", "Prazo", required=False),
        _field("completion_date", "Data de conclusão", required=False, aliases=("conclusao",)),
        _field("status", "Status"),
        _field("process_number", "Processo", aliases=("numero do processo",)),
        _field("notes", "Observação", required=False, aliases=("observacoes", "notas")),
    ),
    SpreadsheetImport.EntityType.INVOICE: (
        _field("work_order_number", "Número da OS", aliases=("os",)),
        _field("number", "Número da NF", aliases=("nf", "nota fiscal", "numero")),
        _field("series", "Série"),
        _field("supplier_name", "Fornecedor"),
        _field("supplier_tax_id", "CNPJ/CPF"),
        _field("issue_date", "Data de emissão", aliases=("data",)),
        _field("competence", "Competência"),
        _field("gross_value", "Valor bruto", aliases=("valor",)),
        _field("deduction_value", "Glosa", required=False),
        _field("accepted_value", "Valor aceito"),
        _field("process_number", "Processo", required=False),
        _field("status", "Status"),
        _field("document_reference", "Referência documental", required=False),
        _field("document_hash", "SHA-256 do documento", required=False),
        _field("notes", "Observação", required=False, aliases=("observacoes", "notas")),
    ),
}

TARGET_PERMISSIONS = {
    SpreadsheetImport.EntityType.COMMITMENT: "contracts.add_budgetcommitment",
    SpreadsheetImport.EntityType.WORK_ORDER: "contracts.add_workorder",
    SpreadsheetImport.EntityType.INVOICE: "contracts.add_invoice",
}


def contract_for_import(actor, contract_id, entity_type):
    if not actor.is_authenticated or not actor.has_perm(TARGET_PERMISSIONS[entity_type]):
        raise PermissionDenied("Permissão de cadastro necessária para importar estes dados.")
    return contracts_writable_by(actor).get(pk=contract_id)


def _cell_text(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def _rows_to_source(rows, *, sheet_name):
    materialized = list(rows)
    if not materialized:
        raise ValidationError(f"A aba {sheet_name} está vazia.")
    headers = [_cell_text(value) for value in materialized[0]]
    while headers and not headers[-1]:
        headers.pop()
    if not headers or any(not header for header in headers):
        raise ValidationError(f"A aba {sheet_name} possui cabeçalho vazio.")
    if len(headers) > MAX_COLUMNS:
        raise ValidationError(f"A aba {sheet_name} excede {MAX_COLUMNS} colunas.")
    folded = [header.casefold() for header in headers]
    if len(folded) != len(set(folded)):
        raise ValidationError(f"A aba {sheet_name} possui cabeçalhos duplicados.")
    parsed = []
    for row_number, values in enumerate(materialized[1:], start=2):
        cells = [_cell_text(value) for value in values[:len(headers)]]
        cells.extend([""] * (len(headers) - len(cells)))
        if not any(cells):
            continue
        if len(parsed) >= MAX_ROWS:
            raise ValidationError(f"Cada importação aceita no máximo {MAX_ROWS} linhas.")
        parsed.append({"row_number": row_number, "values": dict(zip(headers, cells))})
    if not parsed:
        raise ValidationError(f"A aba {sheet_name} não possui linhas de dados.")
    return {"headers": headers, "rows": parsed}


def parse_spreadsheet(uploaded):
    content = uploaded.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValidationError("O arquivo excede o limite de 5 MB.")
    suffix = uploaded.name.rsplit(".", 1)[-1].lower()
    result = {}
    if suffix == "csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("O CSV deve usar codificação UTF-8.") from exc
        try:
            dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        result["CSV"] = _rows_to_source(csv.reader(io.StringIO(text), dialect), sheet_name="CSV")
    elif suffix == "xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                members = archive.infolist()
                if len(members) > 200 or sum(member.file_size for member in members) > 25 * 1024 * 1024:
                    raise ValidationError("O conteúdo descompactado do XLSX excede o limite seguro.")
        except zipfile.BadZipFile as exc:
            raise ValidationError("O arquivo XLSX está inválido ou corrompido.") from exc
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        except Exception as exc:
            raise ValidationError("O arquivo XLSX está inválido ou corrompido.") from exc
        try:
            for worksheet in workbook.worksheets:
                rows = []
                for row in worksheet.iter_rows():
                    values = []
                    for cell in row:
                        if cell.data_type == "f":
                            raise ValidationError(
                                f"A aba {worksheet.title} contém fórmula; substitua por valores antes de importar."
                            )
                        values.append(cell.value)
                    rows.append(values)
                if any(any(value not in (None, "") for value in row) for row in rows):
                    result[worksheet.title] = _rows_to_source(rows, sheet_name=worksheet.title)
        finally:
            workbook.close()
    else:
        raise ValidationError("Envie um arquivo CSV ou XLSX.")
    if not result:
        raise ValidationError("Nenhuma aba com dados foi encontrada.")
    return content, result


@transaction.atomic
def create_import(*, contract, actor, entity_type, uploaded):
    content, source_data = parse_spreadsheet(uploaded)
    digest = hashlib.sha256(content).hexdigest()
    if SpreadsheetImport.objects.filter(
        contract=contract, entity_type=entity_type, content_sha256=digest,
        status=SpreadsheetImport.Status.COMPLETED,
    ).exists():
        raise ValidationError("Este mesmo arquivo já foi importado para o contrato.")
    spreadsheet_import = SpreadsheetImport.objects.create(
        contract=contract,
        created_by=actor,
        entity_type=entity_type,
        file_name=uploaded.name[:255],
        content_sha256=digest,
        source_data=source_data,
    )
    ImportEvent.objects.create(
        spreadsheet_import=spreadsheet_import,
        contract=contract,
        actor=actor,
        event_type=ImportEvent.EventType.UPLOADED,
        details={"arquivo": spreadsheet_import.file_name, "sha256": digest, "abas": list(source_data)},
    )
    return spreadsheet_import


def _decimal(value, label, *, required=True, default=None):
    value = (value or "").strip().replace("R$", "").replace(" ", "")
    if not value:
        if required:
            raise ValidationError(f"{label}: valor obrigatório.")
        return default
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValidationError(f"{label}: número inválido.") from exc


def _date(value, label, *, required=True):
    value = (value or "").strip()
    if not value:
        if required:
            raise ValidationError(f"{label}: data obrigatória.")
        return None
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            pass
    raise ValidationError(f"{label}: use DD/MM/AAAA ou AAAA-MM-DD.")


def _boolean(value, *, default=True):
    value = (value or "").strip().casefold()
    if not value:
        return default
    if value in {"1", "sim", "s", "true", "verdadeiro", "ativo"}:
        return True
    if value in {"0", "não", "nao", "n", "false", "falso", "inativo"}:
        return False
    raise ValidationError("Ativo: informe Sim ou Não.")


def _text(value, label, *, required=True):
    value = " ".join((value or "").split())
    if required and not value:
        raise ValidationError(f"{label}: valor obrigatório.")
    return value


def _status(value):
    raw = _text(value, "Status").casefold()
    for code, label in WorkOrderStatus.choices:
        if raw in {code.casefold(), label.casefold()}:
            return code
    if raw in {"historico_importado", "histórico importado"}:
        return WorkOrderStatus.HISTORICAL_IMPORTED
    raise ValidationError("Status da OS não reconhecido.")


def _mapped_row(spreadsheet_import, source_row):
    return {
        target: source_row["values"].get(source, "") if source else ""
        for target, source in spreadsheet_import.mapping.items()
    }


def _prepare(spreadsheet_import, mapped):
    contract = spreadsheet_import.contract
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.COMMITMENT:
        return {
            "number": _text(mapped["number"], "Número do empenho"),
            "ped": _text(mapped["ped"], "PED"),
            "commitment_date": _date(mapped["commitment_date"], "Data do empenho"),
            "initial_value": _decimal(mapped["initial_value"], "Valor inicial"),
            "source": _text(mapped["source"], "Fonte"),
            "notes": _text(mapped.get("notes"), "Observação", required=False),
            "is_active": _boolean(mapped.get("is_active")),
        }
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.WORK_ORDER:
        item_number = _text(mapped["item_number"], "Número do item")
        items = ContractItem.objects.filter(contract=contract, number__iexact=item_number, is_active=True)
        if items.count() != 1:
            raise ValidationError("Número do item não identifica exatamente um item ativo do contrato.")
        return {
            "number": _text(mapped["number"], "Número da OS"),
            "item": items.get(),
            "description": _text(mapped["description"], "Descrição"),
            "quantity": _decimal(mapped.get("quantity"), "Quantidade", required=False),
            "hours": _decimal(mapped.get("hours"), "Horas", required=False),
            "responsible": _text(mapped["responsible"], "Responsável"),
            "opening_date": _date(mapped["opening_date"], "Data de abertura"),
            "signature_date": _date(mapped.get("signature_date"), "Data de assinatura", required=False),
            "start_date": _date(mapped.get("start_date"), "Data de início", required=False),
            "deadline": _date(mapped.get("deadline"), "Prazo", required=False),
            "completion_date": _date(mapped.get("completion_date"), "Data de conclusão", required=False),
            "status": _status(mapped["status"]),
            "process_number": _text(mapped["process_number"], "Processo"),
            "notes": _text(mapped.get("notes"), "Observação", required=False),
        }
    work_order_number = _text(mapped["work_order_number"], "Número da OS")
    orders = WorkOrder.objects.filter(contract=contract, number__iexact=work_order_number)
    if orders.count() != 1:
        raise ValidationError("Número da OS não identifica exatamente uma OS do contrato.")
    return {
        "work_order": orders.get(),
        "number": _text(mapped["number"], "Número da NF"),
        "series": _text(mapped["series"], "Série"),
        "supplier_name": _text(mapped["supplier_name"], "Fornecedor"),
        "supplier_tax_id": "".join(filter(str.isdigit, mapped["supplier_tax_id"])),
        "issue_date": _date(mapped["issue_date"], "Data de emissão"),
        "competence": _text(mapped["competence"], "Competência"),
        "gross_value": _decimal(mapped["gross_value"], "Valor bruto"),
        "deduction_value": _decimal(mapped.get("deduction_value"), "Glosa", required=False, default=Decimal("0.00")),
        "accepted_value": _decimal(mapped["accepted_value"], "Valor aceito"),
        "process_number": _text(mapped.get("process_number"), "Processo", required=False),
        "status": _text(mapped["status"], "Status"),
        "document_reference": _text(mapped.get("document_reference"), "Referência documental", required=False),
        "document_hash": _text(mapped.get("document_hash"), "SHA-256", required=False).lower(),
        "notes": _text(mapped.get("notes"), "Observação", required=False),
    }


def _duplicate_key(spreadsheet_import, prepared):
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.COMMITMENT:
        return (prepared["number"].casefold(), prepared["ped"].casefold())
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.WORK_ORDER:
        return (prepared["number"].casefold(),)
    return (
        prepared["number"].casefold(), prepared["series"].casefold(), prepared["supplier_tax_id"],
    )


def _already_exists(spreadsheet_import, prepared):
    contract = spreadsheet_import.contract
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.COMMITMENT:
        return BudgetCommitment.objects.filter(
            contract=contract, number__iexact=prepared["number"], ped__iexact=prepared["ped"],
        ).exists()
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.WORK_ORDER:
        return WorkOrder.objects.filter(contract=contract, number__iexact=prepared["number"]).exists()
    return Invoice.objects.filter(
        contract=contract,
        number__iexact=prepared["number"],
        series__iexact=prepared["series"],
        supplier_tax_id=prepared["supplier_tax_id"],
    ).exists()


def _create(spreadsheet_import, actor, prepared):
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.COMMITMENT:
        return create_budget_commitment(contract_id=spreadsheet_import.contract_id, actor=actor, **prepared)
    if spreadsheet_import.entity_type == SpreadsheetImport.EntityType.WORK_ORDER:
        return create_work_order(contract_id=spreadsheet_import.contract_id, actor=actor, **prepared)
    work_order = prepared.pop("work_order")
    return create_invoice(work_order_id=work_order.pk, actor=actor, **prepared)


def _messages(exc):
    if hasattr(exc, "message_dict"):
        return [f"{field}: {message}" for field, messages in exc.message_dict.items() for message in messages]
    if hasattr(exc, "messages"):
        return list(exc.messages)
    return [str(exc)]


@transaction.atomic
def build_preview(*, spreadsheet_import, actor, sheet, mapping):
    contract_for_import(actor, spreadsheet_import.contract_id, spreadsheet_import.entity_type)
    if spreadsheet_import.created_by_id != actor.pk:
        raise PermissionDenied("Somente o autor pode continuar esta importação.")
    if spreadsheet_import.status == SpreadsheetImport.Status.COMPLETED:
        raise ValidationError("A importação já foi concluída.")
    source = spreadsheet_import.source_data.get(sheet)
    if not source:
        raise ValidationError("A aba selecionada não existe no arquivo.")
    spreadsheet_import.selected_sheet = sheet
    spreadsheet_import.mapping = mapping
    preview = []
    seen = set()
    with transaction.atomic():
        for source_row in source["rows"]:
            try:
                prepared = _prepare(spreadsheet_import, _mapped_row(spreadsheet_import, source_row))
                key = _duplicate_key(spreadsheet_import, prepared)
                if key in seen or _already_exists(spreadsheet_import, prepared):
                    status, errors = "DUPLICADO", ["Registro já existente ou repetido no arquivo; não será sobrescrito."]
                else:
                    seen.add(key)
                    _create(spreadsheet_import, actor, prepared.copy())
                    status, errors = "VALIDO", []
            except Exception as exc:
                status, errors = "ERRO", _messages(exc)
            preview.append({
                "row_number": source_row["row_number"],
                "status": status,
                "values": _mapped_row(spreadsheet_import, source_row),
                "errors": errors,
            })
        transaction.set_rollback(True)
    spreadsheet_import.preview = preview
    spreadsheet_import.total_rows = len(preview)
    spreadsheet_import.valid_rows = sum(row["status"] == "VALIDO" for row in preview)
    spreadsheet_import.duplicate_rows = sum(row["status"] == "DUPLICADO" for row in preview)
    spreadsheet_import.error_rows = sum(row["status"] == "ERRO" for row in preview)
    spreadsheet_import.status = SpreadsheetImport.Status.PREVIEWED
    spreadsheet_import.report = {}
    spreadsheet_import.save(update_fields=(
        "selected_sheet", "mapping", "preview", "total_rows", "valid_rows",
        "duplicate_rows", "error_rows", "status", "report",
    ))
    ImportEvent.objects.create(
        spreadsheet_import=spreadsheet_import,
        contract=spreadsheet_import.contract,
        actor=actor,
        event_type=ImportEvent.EventType.PREVIEWED,
        details={
            "aba": sheet, "total": spreadsheet_import.total_rows,
            "validas": spreadsheet_import.valid_rows,
            "duplicadas": spreadsheet_import.duplicate_rows,
            "erros": spreadsheet_import.error_rows,
        },
    )
    return spreadsheet_import


@transaction.atomic
def confirm_import(*, spreadsheet_import_id, actor):
    spreadsheet_import = SpreadsheetImport.objects.select_for_update().select_related("contract").get(
        pk=spreadsheet_import_id
    )
    contract_for_import(actor, spreadsheet_import.contract_id, spreadsheet_import.entity_type)
    if spreadsheet_import.created_by_id != actor.pk:
        raise PermissionDenied("Somente o autor pode confirmar esta importação.")
    if spreadsheet_import.status != SpreadsheetImport.Status.PREVIEWED:
        raise ValidationError("Gere uma prévia atual antes de confirmar.")
    if spreadsheet_import.error_rows:
        raise ValidationError("Corrija todas as linhas com erro antes de confirmar.")
    if not spreadsheet_import.valid_rows:
        raise ValidationError("A prévia não possui registros novos válidos.")
    source_rows = {
        row["row_number"]: row
        for row in spreadsheet_import.source_data[spreadsheet_import.selected_sheet]["rows"]
    }
    imported = []
    for preview_row in spreadsheet_import.preview:
        if preview_row["status"] != "VALIDO":
            continue
        source_row = source_rows[preview_row["row_number"]]
        prepared = _prepare(spreadsheet_import, _mapped_row(spreadsheet_import, source_row))
        if _already_exists(spreadsheet_import, prepared):
            raise ValidationError(
                f"A linha {preview_row['row_number']} passou a conflitar com um registro existente. Gere nova prévia."
            )
        instance = _create(spreadsheet_import, actor, prepared)
        imported.append(instance.pk)
    spreadsheet_import.status = SpreadsheetImport.Status.COMPLETED
    spreadsheet_import.confirmed_at = timezone.now()
    spreadsheet_import.report = {
        "resultado": "concluido",
        "importados": len(imported),
        "duplicados_ignorados": spreadsheet_import.duplicate_rows,
        "identificadores": imported,
    }
    spreadsheet_import.save(update_fields=("status", "confirmed_at", "report"))
    ImportEvent.objects.create(
        spreadsheet_import=spreadsheet_import,
        contract=spreadsheet_import.contract,
        actor=actor,
        event_type=ImportEvent.EventType.COMPLETED,
        details={"atual": spreadsheet_import.report, "sha256": spreadsheet_import.content_sha256},
    )
    return spreadsheet_import


def record_failed_confirmation(*, spreadsheet_import, actor, error):
    ImportEvent.objects.create(
        spreadsheet_import=spreadsheet_import,
        contract=spreadsheet_import.contract,
        actor=actor,
        event_type=ImportEvent.EventType.FAILED,
        details={"erro": "Confirmação rejeitada pelas validações atuais.", "mensagens": _messages(error)},
    )
