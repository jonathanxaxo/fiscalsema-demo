import json

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse

from contracts.accountability import build_accountability_snapshot
from contracts.services import (
    actor_is_active_fiscal, allocations_visible_to, commitments_visible_to, contract_financial_position,
    contracts_visible_to, executions_visible_to, invoice_check_report,
    invoices_visible_to, items_visible_to, payments_visible_to, work_orders_visible_to,
)
from documents.models import DocumentEvent
from documents.services import (
    can_open_document_content,
    document_metadata_visible_to,
    documents_visible_to,
)

from .base import ApiRequestError, ControlledWriteApiView, ReadOnlyApiView
from .drafts import (
    DraftValidationError, create_assistant_draft, create_assistant_draft_batch,
)
from .models import AssistantDraft
from .serializers import (
    allocation_data, commitment_data, contract_data, document_data, execution_data,
    invoice_data, item_data, payment_data, period_data, primitive, work_order_data,
)


PAYMENT_NOTICE = (
    "Consulta informativa. Não constitui atesto, homologação, liquidação, "
    "autorização ou recomendação de pagamento; a decisão exige revisão humana e documental."
)


READ_TOOLS = (
    "contracts.list", "contracts.get", "contracts.summary", "items.list",
    "commitments.list", "work_orders.list", "allocations.list", "executions.list",
    "invoices.list", "invoices.check", "payments.list", "financial.summary",
    "accountability.get", "reports.get", "documents.list", "documents.read",
)
DRAFT_TYPES = tuple(value for value, _label in AssistantDraft.EntityType.choices)


def visible_contract(request, contract_id):
    contract = contracts_visible_to(request.api_actor).filter(pk=contract_id).first()
    if contract is None:
        raise ApiRequestError("not_found", "Recurso não encontrado.", 404)
    request.api_contract = contract
    return contract


def paginated(request, queryset, serializer):
    try:
        page_number = int(request.GET.get("page", "1"))
        page_size = int(request.GET.get("page_size", str(settings.API_DEFAULT_PAGE_SIZE)))
    except ValueError as exc:
        raise ApiRequestError("invalid_pagination", "Paginação deve usar números inteiros positivos.") from exc
    if page_number < 1 or page_size < 1 or page_size > settings.API_MAX_PAGE_SIZE:
        raise ApiRequestError(
            "invalid_pagination",
            f"Use page >= 1 e page_size entre 1 e {settings.API_MAX_PAGE_SIZE}.",
        )
    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(page_number)
    if page_number > max(1, paginator.num_pages):
        raise ApiRequestError("page_not_found", "Página não encontrada.", 404)
    results = [serializer(item) for item in page.object_list]
    request.api_result_count = len(results)
    return {
        "count": paginator.count, "page": page.number, "page_size": page_size,
        "pages": paginator.num_pages, "results": results,
    }


class ContractListView(ReadOnlyApiView):
    def get(self, request):
        return self.json(paginated(request, contracts_visible_to(request.api_actor), contract_data))


class CapabilityView(ReadOnlyApiView):
    def get(self, request):
        read_tools = tuple(
            tool for tool in READ_TOOLS
            if tool != "documents.read" or can_open_document_content(request.api_actor)
        )
        can_draft = (
            request.api_credential.access_mode
            == request.api_credential.AccessMode.CONTROLLED_DRAFT
            and actor_is_active_fiscal(request.api_actor)
        )
        request.api_result_count = len(read_tools) + (len(DRAFT_TYPES) if can_draft else 0)
        return self.json({
            "api_version": "v1",
            "credential_mode": request.api_credential.access_mode,
            "read_tools": read_tools,
            "controlled_drafts": DRAFT_TYPES if can_draft else (),
            "controlled_operations": ("CRIAR", "ATUALIZAR") if can_draft else (),
            "transactional_batches": can_draft,
            "source_comparison": can_draft,
            "optimistic_concurrency_check": can_draft,
            "human_confirmation": True,
            "direct_database_access": False,
        })


class ContractDetailView(ReadOnlyApiView):
    def get(self, request, contract_id):
        request.api_result_count = 1
        return self.json({"data": contract_data(visible_contract(request, contract_id))})


class ContractSummaryView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        request.api_result_count = 1
        return self.json({"data": {
            "contract": contract_data(contract),
            "counts": {
                "items": contract.items.count(),
                "commitments": commitments_visible_to(request.api_actor).filter(contract=contract).count(),
                "work_orders": work_orders_visible_to(request.api_actor).filter(contract=contract).count(),
                "invoices": invoices_visible_to(request.api_actor).filter(contract=contract).count(),
                "payments": payments_visible_to(request.api_actor).filter(invoice__contract=contract).count(),
            },
            "financial": primitive(contract_financial_position(contract)),
            "decision_notice": PAYMENT_NOTICE,
        }})


class ContractCommitmentListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = commitments_visible_to(request.api_actor).filter(contract=contract)
        return self.json(paginated(request, queryset, commitment_data))


class ContractItemListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        return self.json(paginated(
            request, items_visible_to(request.api_actor).filter(contract=contract), item_data,
        ))


class ContractWorkOrderListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = work_orders_visible_to(request.api_actor).filter(contract=contract)
        return self.json(paginated(request, queryset, work_order_data))


class ContractInvoiceListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = invoices_visible_to(request.api_actor).filter(contract=contract)
        return self.json(paginated(request, queryset, invoice_data))


class ContractAllocationListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = allocations_visible_to(request.api_actor).filter(work_order__contract=contract)
        return self.json(paginated(request, queryset, allocation_data))


class ContractExecutionListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = executions_visible_to(request.api_actor).filter(work_order__contract=contract)
        return self.json(paginated(request, queryset, execution_data))


class ContractPaymentListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = payments_visible_to(request.api_actor).filter(invoice__contract=contract)
        data = paginated(request, queryset, payment_data)
        data["decision_notice"] = PAYMENT_NOTICE
        return self.json(data)


class ContractDocumentListView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        queryset = document_metadata_visible_to(request.api_actor).filter(contract=contract)

        def authorized_document_data(document):
            data = document_data(document)
            if not can_open_document_content(request.api_actor):
                data.pop("content_url", None)
            return data

        return self.json(paginated(request, queryset, authorized_document_data))


def accountability_data(snapshot):
    return {
        "contract": contract_data(snapshot.contract),
        "financial": primitive(snapshot.financial_position),
        "commitments": [commitment_data(item) for item in snapshot.commitments],
        "work_orders": [work_order_data(item) for item in snapshot.work_orders],
        "executions": [execution_data(item) for item in snapshot.executions],
        "invoices": [invoice_data(item) for item in snapshot.invoices],
        "payments": [payment_data(item) for item in snapshot.payments],
        "invoice_checks": [
            {"invoice_id": invoice.pk, "check": primitive(check)}
            for invoice, check in snapshot.invoice_checks
        ],
        "annual_periods": {
            "official_closing_rule": "CALENDAR_YEAR",
            "calendar_years": [period_data(item) for item in snapshot.calendar_periods],
            "contract_years": [period_data(item) for item in snapshot.contract_years],
        },
        "decision_notice": PAYMENT_NOTICE,
    }


class ContractAccountabilityView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        request.api_result_count = 1
        return self.json({"data": accountability_data(build_accountability_snapshot(contract, {}))})


class ContractReportView(ContractAccountabilityView):
    pass


class DocumentContentView(ReadOnlyApiView):
    def get(self, request, document_id):
        document = documents_visible_to(request.api_actor).filter(pk=document_id).first()
        if document is None:
            raise ApiRequestError("not_found", "Recurso não encontrado.", 404)
        request.api_contract = document.contract
        request.api_result_count = 1
        DocumentEvent.objects.create(
            event_type=DocumentEvent.EventType.DOWNLOADED,
            document=document, contract=document.contract, actor=request.api_actor,
            details={"origem": "api_v1", "credencial": request.api_credential.token_prefix},
        )
        return FileResponse(
            document.file.open("rb"), as_attachment=True,
            filename=document.original_name, content_type=document.mime_type,
        )


class ContractFinancialSummaryView(ReadOnlyApiView):
    def get(self, request, contract_id):
        contract = visible_contract(request, contract_id)
        request.api_result_count = 1
        return self.json({"data": {
            "contract_id": contract.pk,
            "position": primitive(contract_financial_position(contract)),
            "decision_notice": PAYMENT_NOTICE,
        }})


class InvoiceCheckView(ReadOnlyApiView):
    def get(self, request, invoice_id):
        invoice = invoices_visible_to(request.api_actor).filter(pk=invoice_id).first()
        if invoice is None:
            raise ApiRequestError("not_found", "Recurso não encontrado.", 404)
        request.api_contract = invoice.contract
        request.api_result_count = 1
        return self.json({"data": {
            "invoice": invoice_data(invoice),
            "check": primitive(invoice_check_report(invoice)),
            "decision_notice": PAYMENT_NOTICE,
        }})


def draft_data(draft):
    return {
        "id": draft.pk, "entity_type": draft.entity_type,
        "operation": draft.operation, "batch_id": str(draft.batch_id),
        "contract_id": draft.contract_id, "context": draft.context,
        "payload": draft.payload, "evidence": draft.evidence,
        "source_summary": draft.source_summary,
        "source_authority": draft.source_authority,
        "confidence_level": draft.confidence_level,
        "comparison": draft.comparison,
        "requires_human_confirmation": draft.requires_human_confirmation,
        "consistency_result": draft.consistency_result,
        "status": draft.status,
        "requested_by": {"id": draft.requested_by_id, "name": draft.requested_by.full_name},
        "created_at": draft.created_at.isoformat(),
        "reviewed_at": draft.reviewed_at.isoformat() if draft.reviewed_at else None,
        "target": ({"model": draft.target_model, "id": draft.target_id}
                   if draft.target_id else None),
    }


def draft_batch_preview(drafts):
    classifications = {}
    for draft in drafts:
        for comparison in draft.comparison:
            key = comparison["classification"]
            classifications[key] = classifications.get(key, 0) + 1
    return {
        "draft_count": len(drafts),
        "classification_counts": classifications,
        "all_require_human_confirmation": all(
            draft.requires_human_confirmation for draft in drafts
        ),
    }


class AssistantDraftCreateView(ControlledWriteApiView):
    allowed_methods = {"GET", "POST"}

    def get(self, request):
        queryset = AssistantDraft.objects.select_related("requested_by").filter(
            requested_by=request.api_actor
        )
        return self.json(paginated(request, queryset, draft_data))

    def post(self, request):
        if (
            request.api_credential.access_mode
            != request.api_credential.AccessMode.CONTROLLED_DRAFT
            or not actor_is_active_fiscal(request.api_actor)
        ):
            raise ApiRequestError(
                "insufficient_credential_scope",
                "Esta credencial é somente leitura e não pode criar rascunhos.", 403,
            )
        try:
            body = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ApiRequestError("invalid_json", "Corpo JSON inválido.") from exc
        try:
            draft = create_assistant_draft(
                entity_type=body.get("entity_type"), context=body.get("context", {}),
                payload=body.get("payload", {}), evidence=body.get("evidence", []),
                source_summary=body.get("source_summary", ""),
                operation=body.get("operation", AssistantDraft.Operation.CREATE),
                source_authority=body.get(
                    "source_authority", AssistantDraft.SourceAuthority.AUTOMATED_EXTRACTION,
                ),
                confidence_level=body.get(
                    "confidence_level", AssistantDraft.ConfidenceLevel.FOUND_IN_SOURCE,
                ),
                credential=request.api_credential, actor=request.api_actor,
            )
        except DraftValidationError as exc:
            request.api_error_code = "validation_error"
            response = self.json({
                "error": {"code": "validation_error", "message": str(exc),
                          "fields": exc.errors},
            }, status=400)
            return response
        except PermissionDenied as exc:
            raise ApiRequestError("forbidden", str(exc), 403) from exc
        request.api_contract = draft.contract
        request.api_result_count = 1
        return self.json({
            "data": draft_data(draft),
            "next_action": "O usuário autorizador deve revisar e confirmar na interface web.",
        }, status=201)


class AssistantDraftBatchCreateView(ControlledWriteApiView):
    allowed_methods = {"POST"}

    def post(self, request):
        if (
            request.api_credential.access_mode
            != request.api_credential.AccessMode.CONTROLLED_DRAFT
            or not actor_is_active_fiscal(request.api_actor)
        ):
            raise ApiRequestError(
                "insufficient_credential_scope",
                "Esta credencial é somente leitura e não pode criar rascunhos.", 403,
            )
        try:
            body = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ApiRequestError("invalid_json", "Corpo JSON inválido.") from exc
        try:
            drafts = create_assistant_draft_batch(
                proposals=body.get("proposals", []), credential=request.api_credential,
                actor=request.api_actor,
            )
        except DraftValidationError as exc:
            return self.json({
                "error": {"code": "validation_error", "message": str(exc),
                          "fields": exc.errors},
            }, status=400)
        except PermissionDenied as exc:
            raise ApiRequestError("forbidden", str(exc), 403) from exc
        request.api_result_count = len(drafts)
        request.api_contract = drafts[0].contract if drafts else None
        return self.json({
            "batch_id": str(drafts[0].batch_id),
            "preview": draft_batch_preview(drafts),
            "results": [draft_data(draft) for draft in drafts],
            "next_action": "O usuário autorizador deve revisar e confirmar o lote na interface web.",
        }, status=201)


class AssistantDraftDetailApiView(ReadOnlyApiView):
    def get(self, request, draft_id):
        draft = AssistantDraft.objects.select_related("requested_by").filter(
            pk=draft_id, requested_by=request.api_actor,
        ).first()
        if draft is None:
            raise ApiRequestError("not_found", "Recurso não encontrado.", 404)
        request.api_contract = draft.contract
        request.api_result_count = 1
        return self.json({"data": draft_data(draft)})
