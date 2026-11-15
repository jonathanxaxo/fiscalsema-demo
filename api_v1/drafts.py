import hashlib
import json
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.forms.models import model_to_dict
from django.db import transaction
from django.utils import timezone

from contracts.accountability import build_accountability_snapshot
from contracts.forms import (
    BudgetCommitmentForm, ContractForm, ContractItemForm, InvoiceForm, PaymentForm,
    WorkOrderAllocationForm, WorkOrderExecutionForm, WorkOrderForm,
)
from contracts.services import (
    allocations_writable_by, commitments_writable_by, contract_financial_position,
    contracts_writable_by, create_budget_commitment, create_contract,
    create_contract_item, create_invoice, create_payment, create_work_order,
    create_work_order_allocation, create_work_order_execution,
    executions_writable_by, invoices_writable_by, items_writable_by,
    payments_writable_by, require_contract_creator, update_budget_commitment,
    update_contract, update_contract_item, update_invoice, update_payment,
    update_work_order, update_work_order_allocation, update_work_order_execution,
    work_orders_writable_by,
)
from documents.models import Document

from .models import AssistantDraft, AssistantDraftEvent
from .serializers import primitive


class DraftValidationError(ValidationError):
    def __init__(self, message, *, errors=None):
        super().__init__(message)
        self.errors = errors or {}


FORM_CLASSES = {
    AssistantDraft.EntityType.CONTRACT: ContractForm,
    AssistantDraft.EntityType.ITEM: ContractItemForm,
    AssistantDraft.EntityType.COMMITMENT: BudgetCommitmentForm,
    AssistantDraft.EntityType.WORK_ORDER: WorkOrderForm,
    AssistantDraft.EntityType.ALLOCATION: WorkOrderAllocationForm,
    AssistantDraft.EntityType.EXECUTION: WorkOrderExecutionForm,
    AssistantDraft.EntityType.INVOICE: InvoiceForm,
    AssistantDraft.EntityType.PAYMENT: PaymentForm,
}

TARGET_QUERYSETS = {
    AssistantDraft.EntityType.CONTRACT: contracts_writable_by,
    AssistantDraft.EntityType.ITEM: items_writable_by,
    AssistantDraft.EntityType.COMMITMENT: commitments_writable_by,
    AssistantDraft.EntityType.WORK_ORDER: work_orders_writable_by,
    AssistantDraft.EntityType.ALLOCATION: allocations_writable_by,
    AssistantDraft.EntityType.EXECUTION: executions_writable_by,
    AssistantDraft.EntityType.INVOICE: invoices_writable_by,
    AssistantDraft.EntityType.PAYMENT: payments_writable_by,
}

CRITICAL_FIELDS = {
    AssistantDraft.EntityType.CONTRACT: {
        "number", "process_number", "supplier_tax_id", "validity_start",
        "validity_end", "original_value", "status",
    },
    AssistantDraft.EntityType.ITEM: {
        "number", "unit", "contracted_quantity", "annual_reference_quantity",
        "annual_reference_unit", "annual_operational_limit", "unit_value", "is_active",
    },
    AssistantDraft.EntityType.COMMITMENT: {
        "number", "commitment_date", "initial_value", "is_active",
    },
    AssistantDraft.EntityType.WORK_ORDER: {
        "number", "item", "quantity", "hours", "deadline", "completion_date", "status",
    },
    AssistantDraft.EntityType.ALLOCATION: {"commitment", "amount", "status"},
    AssistantDraft.EntityType.EXECUTION: {"executed_quantity", "executed_value", "execution_date"},
    AssistantDraft.EntityType.INVOICE: {
        "item", "allocation", "number", "supplier_tax_id", "issue_date",
        "gross_value", "deduction_value", "accepted_value", "status",
    },
    AssistantDraft.EntityType.PAYMENT: {"amount", "payment_date", "status"},
}

LOW_CONFIDENCE = {
    AssistantDraft.ConfidenceLevel.INFERRED,
    AssistantDraft.ConfidenceLevel.ESTIMATED,
    AssistantDraft.ConfidenceLevel.PENDING,
    AssistantDraft.ConfidenceLevel.DIVERGENT,
}


def _jsonable(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "pk"):
        return value.pk
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _stable_hash(value):
    serialized = json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _target_contract(target):
    if target is None:
        return None
    if hasattr(target, "contract"):
        return target.contract
    if hasattr(target, "work_order"):
        return target.work_order.contract
    if hasattr(target, "invoice"):
        return target.invoice.contract
    return target


def _target_for(*, entity_type, operation, context, actor):
    if operation == AssistantDraft.Operation.CREATE:
        return None
    if operation != AssistantDraft.Operation.UPDATE:
        raise DraftValidationError("Operação de rascunho inválida.")
    target_id = context.get("target_id")
    if not target_id:
        raise DraftValidationError("Atualização exige context.target_id.")
    queryset_factory = TARGET_QUERYSETS.get(entity_type)
    if queryset_factory is None:
        raise DraftValidationError("Tipo de rascunho inválido.")
    target = queryset_factory(actor).filter(pk=target_id).first()
    if target is None:
        raise PermissionDenied("Registro não encontrado no escopo de escrita do usuário.")
    return target


def _merged_update_payload(form_class, target, payload):
    fields = form_class.Meta.fields
    merged = model_to_dict(target, fields=fields)
    merged.update(payload)
    return merged


def _form_for(*, entity_type, operation, context, payload, actor):
    target = _target_for(
        entity_type=entity_type, operation=operation, context=context, actor=actor,
    )
    contract = _target_contract(target)
    parent = None
    form_class = FORM_CLASSES.get(entity_type)
    if form_class is None:
        raise DraftValidationError("Tipo de rascunho inválido.")
    form_payload = (
        _merged_update_payload(form_class, target, payload)
        if target is not None else payload
    )

    if entity_type == AssistantDraft.EntityType.CONTRACT:
        if target is None:
            require_contract_creator(actor)
        form = ContractForm(form_payload, instance=target)
    elif entity_type in {
        AssistantDraft.EntityType.ITEM,
        AssistantDraft.EntityType.COMMITMENT,
        AssistantDraft.EntityType.WORK_ORDER,
    }:
        if target is None:
            contract = contracts_writable_by(actor).filter(pk=context.get("contract_id")).first()
            if contract is None:
                raise PermissionDenied("Contrato não encontrado no escopo de escrita do usuário.")
        if entity_type == AssistantDraft.EntityType.WORK_ORDER:
            form = WorkOrderForm(form_payload, contract=contract, instance=target)
        else:
            form = form_class(form_payload, instance=target)
    elif entity_type in {
        AssistantDraft.EntityType.ALLOCATION,
        AssistantDraft.EntityType.EXECUTION,
        AssistantDraft.EntityType.INVOICE,
    }:
        if target is None:
            parent = work_orders_writable_by(actor).filter(
                pk=context.get("work_order_id")
            ).first()
            if parent is None:
                raise PermissionDenied("OS não encontrada no escopo de escrita do usuário.")
            contract = parent.contract
        else:
            parent = target.work_order
        if entity_type in {
            AssistantDraft.EntityType.ALLOCATION,
            AssistantDraft.EntityType.INVOICE,
        }:
            form = form_class(form_payload, work_order=parent, instance=target)
        else:
            form = form_class(form_payload, instance=target)
    elif entity_type == AssistantDraft.EntityType.PAYMENT:
        if target is None:
            parent = invoices_writable_by(actor).filter(pk=context.get("invoice_id")).first()
            if parent is None:
                raise PermissionDenied("NF não encontrada no escopo de escrita do usuário.")
            contract = parent.contract
        else:
            parent = target.invoice
        form = PaymentForm(form_payload, invoice=parent, instance=target)
    return form, contract, parent, target


def _validate_evidence(evidence, contract, actor):
    if not isinstance(evidence, list) or not evidence:
        raise DraftValidationError("Informe ao menos uma fonte ou evidência.")
    normalized = []
    for entry in evidence:
        if not isinstance(entry, dict) or not str(entry.get("source", "")).strip():
            raise DraftValidationError("Cada evidência precisa identificar a fonte.")
        safe = {
            "source": str(entry["source"]).strip(),
            "reference": str(entry.get("reference", "")).strip(),
            "excerpt": str(entry.get("excerpt", "")).strip()[:2000],
            # Caminho só é autorizado quando resolvido de um Document interno.
            # Um texto enviado pela integração não pode se autodeclarar autorizado.
            "authorized_path": "",
            "field": str(entry.get("field", "")).strip()[:100],
            "extracted_value": _jsonable(entry.get("extracted_value")),
            "confidence": str(entry.get("confidence", "")).strip()[:30],
            "validation_result": str(entry.get("validation_result", "")).strip()[:100],
            "observed_at": str(entry.get("observed_at", "")).strip()[:40],
        }
        document_id = entry.get("document_id")
        if document_id is not None:
            if contract is None:
                raise DraftValidationError("Documento interno exige contrato já existente.")
            document = Document.objects.filter(pk=document_id, contract=contract).first()
            if document is None:
                raise PermissionDenied("Documento não encontrado no contrato autorizado.")
            safe.update({
                "document_id": document.pk,
                "filename": document.original_name,
                "authorized_path": document.file.name,
                "document_sha256": document.sha256,
                "observed_at": document.uploaded_at.isoformat(),
            })
        normalized.append(safe)
    return normalized


def _current_values(target, payload):
    if target is None:
        return {field: None for field in payload}
    values = {}
    for field in payload:
        model_field = target._meta.get_field(field)
        if model_field.is_relation:
            values[field] = getattr(target, f"{field}_id")
        else:
            values[field] = getattr(target, field)
    return _jsonable(values)


def _comparison(*, entity_type, operation, payload, current_values, confidence_level,
                source_authority):
    rows = []
    for field, proposed in payload.items():
        current = current_values.get(field)
        proposed = _jsonable(proposed)
        if str(current) == str(proposed):
            classification = "IGUAL"
        elif proposed in (None, "") and current not in (None, ""):
            classification = "AUSENTE"
        elif confidence_level == AssistantDraft.ConfidenceLevel.PENDING:
            classification = "PENDENTE_DE_CONFIRMACAO"
        elif confidence_level == AssistantDraft.ConfidenceLevel.DIVERGENT:
            classification = "DIVERGENTE"
        elif confidence_level in LOW_CONFIDENCE:
            classification = "NAO_CONFIAVEL"
        elif current in (None, ""):
            classification = "NOVO"
        elif field in CRITICAL_FIELDS.get(entity_type, set()):
            classification = "DIVERGENTE"
        else:
            classification = "ALTERADO"
        rows.append({
            "field": field,
            "current": current,
            "proposed": proposed,
            "classification": classification,
            "critical": field in CRITICAL_FIELDS.get(entity_type, set()),
            "source_precedence": (
                "CONFIRMACAO_OBRIGATORIA"
                if operation == AssistantDraft.Operation.UPDATE
                and source_authority != AssistantDraft.SourceAuthority.VALIDATED_SYSTEM
                else "COMPATIVEL"
            ),
        })
    return rows


def validate_draft(*, entity_type, operation, context, payload, evidence, actor):
    if entity_type not in AssistantDraft.EntityType.values:
        raise DraftValidationError("Tipo de rascunho inválido.")
    if operation not in AssistantDraft.Operation.values:
        raise DraftValidationError("Operação de rascunho inválida.")
    if not isinstance(context, dict) or not isinstance(payload, dict):
        raise DraftValidationError("Contexto e dados propostos devem ser objetos JSON.")
    allowed_fields = set(FORM_CLASSES[entity_type].Meta.fields)
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        raise DraftValidationError(
            "Os dados propostos contêm campos desconhecidos.",
            errors={"payload": unknown_fields},
        )
    form, contract, parent, target = _form_for(
        entity_type=entity_type, operation=operation, context=context,
        payload=payload, actor=actor,
    )
    if not payload:
        raise DraftValidationError("Informe ao menos um campo proposto.")
    if not form.is_valid():
        raise DraftValidationError(
            "Os dados propostos não passaram na validação.",
            errors={key: [str(item) for item in values] for key, values in form.errors.items()},
        )
    return (
        form, contract, parent, target,
        _validate_evidence(evidence, contract, actor),
    )


@transaction.atomic
def create_assistant_draft(*, entity_type, context, payload, evidence, source_summary,
                           credential=None, actor, operation=AssistantDraft.Operation.CREATE,
                           application=None, expires_at=None, idempotency_key="",
                           source_authority=AssistantDraft.SourceAuthority.AUTOMATED_EXTRACTION,
                           confidence_level=AssistantDraft.ConfidenceLevel.FOUND_IN_SOURCE,
                           batch_id=None):
    if (credential is None) == (application is None):
        raise DraftValidationError("Origem técnica do rascunho inválida.")
    source_summary = " ".join(str(source_summary or "").split())
    if not source_summary:
        raise DraftValidationError("Informe um resumo da origem dos dados.")
    if source_authority not in AssistantDraft.SourceAuthority.values:
        raise DraftValidationError("Autoridade da fonte inválida.")
    if source_authority == AssistantDraft.SourceAuthority.VALIDATED_SYSTEM:
        raise DraftValidationError(
            "A integração não pode declarar sua proposta como dado homologado no sistema."
        )
    if confidence_level not in AssistantDraft.ConfidenceLevel.values:
        raise DraftValidationError("Nível de confiança inválido.")
    form, contract, _parent, target, normalized_evidence = validate_draft(
        entity_type=entity_type, operation=operation, context=context, payload=payload,
        evidence=evidence, actor=actor,
    )
    # ModelForm.is_valid() aplica os valores limpos à instância em memória.
    # Recarregamos o alvo antes de comparar para preservar o estado oficial atual.
    if target is not None:
        target.refresh_from_db()
    current_values = _current_values(target, payload)
    comparison = _comparison(
        entity_type=entity_type, operation=operation, payload=payload,
        current_values=current_values, confidence_level=confidence_level,
        source_authority=source_authority,
    )
    draft = AssistantDraft.objects.create(
        entity_type=entity_type, operation=operation, batch_id=batch_id or uuid.uuid4(),
        contract=contract, context=context, payload=payload, evidence=normalized_evidence,
        source_summary=source_summary, source_authority=source_authority,
        confidence_level=confidence_level, comparison=comparison,
        baseline_hash=_stable_hash(current_values),
        target_model=target._meta.label_lower if target else "",
        target_id=target.pk if target else None,
        created_by_credential=credential, created_by_application=application,
        requested_by=actor, expires_at=expires_at, idempotency_key=idempotency_key or "",
    )
    AssistantDraftEvent.objects.create(
        event_type=AssistantDraftEvent.EventType.CREATED, draft=draft,
        contract=contract, actor=actor,
        details={
            "tipo": entity_type, "operacao": operation, "lote": str(draft.batch_id),
            "dados_propostos": payload, "comparacao": comparison,
            "fontes": normalized_evidence, "autoridade_fonte": source_authority,
            "confianca": confidence_level, "resultado": "pendente_revisao",
            "origem": "mcp_oauth" if application is not None else "api_v1",
        },
    )
    return draft


@transaction.atomic
def create_assistant_draft_batch(*, proposals, credential, actor):
    if not isinstance(proposals, list) or not proposals:
        raise DraftValidationError("Informe uma lista não vazia de propostas.")
    if len(proposals) > 50:
        raise DraftValidationError("Cada lote pode conter no máximo 50 propostas.")
    batch_id = uuid.uuid4()
    return [
        create_assistant_draft(
            entity_type=item.get("entity_type"), operation=item.get("operation", "CRIAR"),
            context=item.get("context", {}), payload=item.get("payload", {}),
            evidence=item.get("evidence", []), source_summary=item.get("source_summary", ""),
            source_authority=item.get(
                "source_authority", AssistantDraft.SourceAuthority.AUTOMATED_EXTRACTION,
            ),
            confidence_level=item.get(
                "confidence_level", AssistantDraft.ConfidenceLevel.FOUND_IN_SOURCE,
            ),
            credential=credential, actor=actor, batch_id=batch_id,
        )
        for item in proposals
    ]


def _persist(form, draft, actor, parent):
    data = form.cleaned_data
    kind = draft.entity_type
    if draft.operation == AssistantDraft.Operation.UPDATE:
        functions = {
            AssistantDraft.EntityType.CONTRACT: (update_contract, "contract_id"),
            AssistantDraft.EntityType.ITEM: (update_contract_item, "item_id"),
            AssistantDraft.EntityType.COMMITMENT: (update_budget_commitment, "commitment_id"),
            AssistantDraft.EntityType.WORK_ORDER: (update_work_order, "work_order_id"),
            AssistantDraft.EntityType.ALLOCATION: (update_work_order_allocation, "allocation_id"),
            AssistantDraft.EntityType.EXECUTION: (update_work_order_execution, "execution_id"),
            AssistantDraft.EntityType.INVOICE: (update_invoice, "invoice_id"),
            AssistantDraft.EntityType.PAYMENT: (update_payment, "payment_id"),
        }
        function, id_name = functions[kind]
        return function(actor=actor, **{id_name: draft.target_id}, **data)
    if kind == AssistantDraft.EntityType.CONTRACT:
        return create_contract(actor=actor, **data)
    if kind == AssistantDraft.EntityType.ITEM:
        return create_contract_item(contract_id=draft.contract_id, actor=actor, **data)
    if kind == AssistantDraft.EntityType.COMMITMENT:
        return create_budget_commitment(contract_id=draft.contract_id, actor=actor, **data)
    if kind == AssistantDraft.EntityType.WORK_ORDER:
        return create_work_order(contract_id=draft.contract_id, actor=actor, **data)
    if kind == AssistantDraft.EntityType.ALLOCATION:
        return create_work_order_allocation(work_order_id=parent.pk, actor=actor, **data)
    if kind == AssistantDraft.EntityType.EXECUTION:
        return create_work_order_execution(work_order_id=parent.pk, actor=actor, **data)
    if kind == AssistantDraft.EntityType.INVOICE:
        return create_invoice(work_order_id=parent.pk, actor=actor, **data)
    if kind == AssistantDraft.EntityType.PAYMENT:
        return create_payment(invoice_id=parent.pk, actor=actor, **data)
    raise DraftValidationError("Tipo de rascunho inválido.")


def _consistency_result(target):
    contract = _target_contract(target)
    target.full_clean()
    financial_position = primitive(contract_financial_position(contract))
    accountability_position = primitive(
        build_accountability_snapshot(contract, {}).financial_position
    )
    return {
        "status": "VALIDADO",
        "validated_at": timezone.now().isoformat(),
        "contract_id": contract.pk,
        "financial_position": financial_position,
        "accountability_matches": accountability_position == financial_position,
        "api_uses_same_financial_service": True,
        "source": "contracts.services.contract_financial_position",
    }


def confirm_assistant_draft(*, draft_id, actor, channel="web"):
    try:
        with transaction.atomic():
            draft = AssistantDraft.objects.select_for_update().get(pk=draft_id)
            if draft.requested_by_id != actor.pk:
                raise PermissionDenied("Somente o usuário autorizador pode confirmar este rascunho.")
            if draft.status != AssistantDraft.Status.PENDING:
                raise DraftValidationError("Este rascunho já foi revisado.")
            if draft.expires_at and draft.expires_at <= timezone.now():
                raise DraftValidationError("Esta proposta venceu. Peça à IA uma nova proposta.")
            form, contract, parent, target, _evidence = validate_draft(
                entity_type=draft.entity_type, operation=draft.operation,
                context=draft.context, payload=draft.payload,
                evidence=draft.evidence, actor=actor,
            )
            if draft.operation == AssistantDraft.Operation.UPDATE:
                target.refresh_from_db()
                current_hash = _stable_hash(_current_values(target, draft.payload))
                if current_hash != draft.baseline_hash:
                    raise DraftValidationError(
                        "O registro mudou depois da comparação. Gere um novo rascunho antes de confirmar."
                    )
            persisted = _persist(form, draft, actor, parent)
            consistency = _consistency_result(persisted)
            effective_values = _current_values(persisted, draft.payload)
            draft.status = AssistantDraft.Status.CONFIRMED
            draft.reviewed_by = actor
            draft.reviewed_at = timezone.now()
            draft.target_model = persisted._meta.label_lower
            draft.target_id = persisted.pk
            draft.consistency_result = consistency
            if draft.contract_id is None and draft.entity_type == AssistantDraft.EntityType.CONTRACT:
                draft.contract = persisted
            draft.save(update_fields=(
                "status", "reviewed_by", "reviewed_at", "target_model", "target_id",
                "contract", "consistency_result",
            ))
            AssistantDraftEvent.objects.create(
                event_type=AssistantDraftEvent.EventType.CONFIRMED, draft=draft,
                contract=draft.contract, actor=actor,
                details={
                    "tipo": draft.entity_type, "operacao": draft.operation,
                    "dados_propostos": draft.payload, "comparacao": draft.comparison,
                    "fontes": draft.evidence, "confirmacao_humana": True,
                    "canal": channel,
                    "valor_efetivamente_gravado": effective_values,
                    "resultado": "gravado", "consistencia": consistency,
                    "registro": {"modelo": draft.target_model, "id": draft.target_id},
                },
            )
            return draft, persisted
    except (ValidationError, PermissionDenied) as exc:
        failed = AssistantDraft.objects.filter(pk=draft_id).first()
        if failed is not None and failed.status == AssistantDraft.Status.PENDING:
            AssistantDraftEvent.objects.create(
                event_type=AssistantDraftEvent.EventType.VALIDATION_FAILED,
                draft=failed, contract=failed.contract, actor=actor,
                details={"resultado": "recusado_pela_validacao", "erro": str(exc)},
            )
        raise


@transaction.atomic
def confirm_assistant_draft_batch(*, batch_id, actor):
    drafts = list(
        AssistantDraft.objects.select_for_update().filter(
            batch_id=batch_id, requested_by=actor,
        ).order_by("pk")
    )
    if not drafts:
        raise DraftValidationError("Lote não encontrado.")
    if any(draft.status != AssistantDraft.Status.PENDING for draft in drafts):
        raise DraftValidationError("O lote contém rascunho já revisado.")
    return [confirm_assistant_draft(draft_id=draft.pk, actor=actor) for draft in drafts]


@transaction.atomic
def reject_assistant_draft(*, draft_id, actor, reason):
    draft = AssistantDraft.objects.select_for_update().get(pk=draft_id)
    if draft.requested_by_id != actor.pk:
        raise PermissionDenied("Somente o usuário autorizador pode rejeitar este rascunho.")
    if draft.status != AssistantDraft.Status.PENDING:
        raise DraftValidationError("Este rascunho já foi revisado.")
    reason = " ".join(str(reason or "").split())
    if not reason:
        raise DraftValidationError("Informe o motivo da rejeição.")
    draft.status = AssistantDraft.Status.REJECTED
    draft.reviewed_by = actor
    draft.reviewed_at = timezone.now()
    draft.rejection_reason = reason
    draft.save(update_fields=("status", "reviewed_by", "reviewed_at", "rejection_reason"))
    AssistantDraftEvent.objects.create(
        event_type=AssistantDraftEvent.EventType.REJECTED, draft=draft,
        contract=draft.contract, actor=actor,
        details={"confirmacao_humana": True, "resultado": "rejeitado", "motivo": reason},
    )
    return draft
