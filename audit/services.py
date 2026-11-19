import json
from dataclasses import dataclass

from django.core.paginator import Page, Paginator
from django.db.models import Q

from accounts.models import AuthenticationEvent
from contracts.models import (
    BudgetCommitmentEvent,
    ContractEvent,
    CsvExportEvent,
    ContractItemEvent,
    ContractIntelligenceEvent,
    ContractSharingEvent,
    FiscalSubstitutionEvent,
    InvoiceEvent,
    PaymentEvent,
    WorkOrderAllocationEvent,
    WorkOrderEvent,
    WorkOrderExecutionEvent,
)
from documents.models import DocumentEvent
from data_imports.models import ImportEvent
from organizations.models import OrganizationEvent
from api_v1.models import ApiAccessEvent, AssistantDraftEvent


SENSITIVE_FRAGMENTS = (
    "password", "senha", "token", "secret", "segredo", "cookie", "session",
    "authorization", "private_key", "chave_privada",
)


@dataclass(frozen=True)
class AuditEntry:
    timestamp: object
    category: str
    action: str
    actor: str
    organization: str
    contract: str
    record: str
    previous_json: str
    current_json: str
    details_json: str
    source_id: str


def _safe_value(value):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized = str(key).casefold()
            result[str(key)] = (
                "[PROTEGIDO]"
                if any(fragment in normalized for fragment in SENSITIVE_FRAGMENTS)
                else _safe_value(item)
            )
        return result
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return value


def _json(value):
    if value in (None, {}, []):
        return ""
    return json.dumps(_safe_value(value), ensure_ascii=False, indent=2, default=str)


def _actor_name(event, field="actor"):
    actor = getattr(event, field, None)
    return actor.full_name if actor else "Sistema/usuário removido"


def _contract_organization(event):
    return event.contract.contracting_organization.name


def _normalize(event, category, record, actor_field="actor", contract=None, organization=None):
    details = _safe_value(event.details or {})
    previous = details.pop("anterior", None)
    current = details.pop("atual", None)
    contract_object = contract if contract is not None else getattr(event, "contract", None)
    organization_name = organization or (
        contract_object.contracting_organization.name if contract_object else "—"
    )
    return AuditEntry(
        timestamp=event.created_at,
        category=category,
        action=event.get_event_type_display(),
        actor=_actor_name(event, actor_field),
        organization=organization_name,
        contract=contract_object.number if contract_object else "—",
        record=record(event),
        previous_json=_json(previous),
        current_json=_json(current),
        details_json=_json(details),
        source_id=f"{event._meta.label_lower}:{event.pk}",
    )


def _contract_sources(contract=None):
    sources = [
        (ContractEvent, "CONTRATO", lambda e: f"Contrato {e.contract.number}"),
        (ContractItemEvent, "ITEM", lambda e: f"Item {e.item.number}"),
        (BudgetCommitmentEvent, "EMPENHO", lambda e: f"Empenho {e.commitment.number}"),
        (WorkOrderAllocationEvent, "RATEIO", lambda e: f"Rateio {e.allocation_id}"),
        (WorkOrderEvent, "OS", lambda e: f"OS {e.work_order.number}"),
        (WorkOrderExecutionEvent, "EXECUCAO", lambda e: f"Execução {e.execution_id}"),
        (InvoiceEvent, "NF", lambda e: f"NF {e.invoice.number}/{e.invoice.series}"),
        (PaymentEvent, "PAGAMENTO", lambda e: f"Pagamento {e.payment_id}"),
        (
            ContractSharingEvent,
            "COMPARTILHAMENTO",
            lambda e: f"Acesso {e.access_id}" if e.access_id else f"Convite {e.invitation_id}",
        ),
        (
            FiscalSubstitutionEvent,
            "SUBSTITUICAO_FISCAL",
            lambda e: f"Substituição {e.substitution.email}",
        ),
        (DocumentEvent, "DOCUMENTO", lambda e: f"Documento {e.document.title} v{e.document.version}"),
        (ImportEvent, "IMPORTACAO", lambda e: f"Importação {e.spreadsheet_import_id} — {e.spreadsheet_import.file_name}"),
        (CsvExportEvent, "EXPORTACAO", lambda e: f"CSV do contrato {e.contract.number}"),
        (
            ContractIntelligenceEvent,
            "INTELIGENCIA_CONTRATUAL",
            lambda e: (
                f"Achado {e.finding.code}" if e.finding_id else
                f"Regra {e.rule.code}" if e.rule_id else
                f"Execução {e.execution_id}" if e.execution_id else
                f"Cláusula {e.details.get('clausula_id')}" if e.details.get("clausula_id") else
                f"Classificação {e.classification_id}"
            ),
        ),
        (AssistantDraftEvent, "ASSISTENTE_IA", lambda e: f"Rascunho #{e.draft_id} — {e.draft.get_entity_type_display()}"),
    ]
    return [
        {
            "queryset": model.objects.filter(contract=contract) if contract else model.objects.all(),
            "category": category,
            "record": record,
            "actor_field": "actor",
        }
        for model, category, record in sources
    ]


def _global_sources():
    sources = _contract_sources()
    sources.extend(
        (
            {
                "queryset": AuthenticationEvent.objects.all(),
                "category": "AUTENTICACAO",
                "record": lambda e: e.user.full_name if e.user else "Identificador protegido",
                "actor_field": "user",
            },
            {
                "queryset": OrganizationEvent.objects.all(),
                "category": "ORGANIZACAO",
                "record": lambda e: (
                    str(e.sector) if e.sector_id else str(e.organization)
                    if e.organization_id else str(e.user) if e.user_id else "Registro institucional"
                ),
                "actor_field": "actor",
            },
            {
                "queryset": ApiAccessEvent.objects.all(),
                "category": "API",
                "record": lambda e: (
                    f"Assistente Arise — pergunta ({e.status_code})"
                    if e.endpoint == "/assistente/"
                    else f"{e.method} {e.endpoint} ({e.status_code})"
                ),
                "actor_field": "actor",
            },
        )
    )
    return sources


def build_audit_page(*, filters, page_number, contract=None, include_global=False, per_page=25):
    selected_category = filters.get("categoria") or ""
    actor_query = (filters.get("usuario") or "").strip()
    sources = _global_sources() if include_global else _contract_sources(contract)
    prepared = []
    total = 0
    for source in sources:
        if selected_category and source["category"] != selected_category:
            continue
        queryset = source["queryset"].select_related()
        if filters.get("inicio"):
            queryset = queryset.filter(created_at__date__gte=filters["inicio"])
        if filters.get("fim"):
            queryset = queryset.filter(created_at__date__lte=filters["fim"])
        if actor_query:
            actor_field = source["actor_field"]
            queryset = queryset.filter(
                Q(**{f"{actor_field}__full_name__icontains": actor_query})
                | Q(**{f"{actor_field}__email__icontains": actor_query})
            )
        queryset = queryset.order_by("-created_at", "-pk")
        count = queryset.count()
        total += count
        prepared.append((source, queryset))

    paginator = Paginator(range(total), per_page)
    numbered_page = paginator.get_page(page_number)
    limit = numbered_page.number * per_page
    entries = []
    for source, queryset in prepared:
        for event in queryset[:limit]:
            if source["category"] == "AUTENTICACAO":
                organization = event.user.organization.name if event.user and event.user.organization_id else "—"
                entry = _normalize(
                    event, source["category"], source["record"],
                    actor_field=source["actor_field"], organization=organization,
                )
            elif source["category"] == "ORGANIZACAO":
                organization = event.organization.name if event.organization_id else (
                    event.sector.organization.name if event.sector_id else "—"
                )
                entry = _normalize(
                    event, source["category"], source["record"], organization=organization,
                )
            elif source["category"] == "API":
                organization = (
                    event.actor.organization.name
                    if event.actor and event.actor.organization_id else "—"
                )
                entry = _normalize(
                    event, source["category"], source["record"],
                    actor_field=source["actor_field"], contract=event.contract,
                    organization=organization,
                )
            else:
                entry = _normalize(event, source["category"], source["record"])
            entries.append(entry)
    entries.sort(key=lambda e: (e.timestamp, e.source_id), reverse=True)
    offset = (numbered_page.number - 1) * per_page
    return Page(entries[offset:offset + per_page], numbered_page.number, paginator)
