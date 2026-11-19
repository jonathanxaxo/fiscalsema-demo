"""Motor contratual determinístico e explicável do FiscalSema Demo.

O módulo não executa SQL livre, não chama IA e não transforma detecções em
regras oficiais. Toda consulta passa pelos serviços de autorização existentes.
"""

from dataclasses import dataclass
from decimal import Decimal
import unicodedata

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .calculations import NegativeBalanceError, calculate_item_total
from .models import (
    ContractClassification,
    ContractClause,
    ContractClauseType,
    ContractFinding,
    ContractFindingSeverity,
    ContractFindingStatus,
    ContractIntelligenceEvent,
    ContractItemClassification,
    ContractItemUnit,
    ContractManagementCategory,
    ContractModality,
    ContractRule,
    ContractRuleType,
    IntelligenceExecution,
    IntelligenceReviewStatus,
    WorkOrderStatus,
)
from .services import (
    contract_financial_position,
    contracts_scannable_by,
    contracts_visible_to,
    contracts_writable_by,
    item_financial_position,
)


BR_TIC_FISCALIZATION = "BR_TIC_FISCALIZATION"
CALCULATOR_QUANTITY_X_UNIT_VALUE = "QUANTITY_X_UNIT_VALUE"
ALLOWED_CALCULATORS = {CALCULATOR_QUANTITY_X_UNIT_VALUE}
ACTIVE_FINDING_STATUSES = (
    ContractFindingStatus.NEW,
    ContractFindingStatus.READ,
    ContractFindingStatus.IN_ANALYSIS,
    ContractFindingStatus.AWAITING_INFORMATION,
)

UNIT_MODALITIES = {
    ContractItemUnit.HOUR: ContractModality.HOUR,
    ContractItemUnit.UNIT: ContractModality.UNIT,
    ContractItemUnit.MONTH: ContractModality.MONTHLY,
    ContractItemUnit.SERVICE: ContractModality.SERVICE,
    ContractItemUnit.LICENSE: ContractModality.LICENSE,
    ContractItemUnit.USER: ContractModality.USER,
    ContractItemUnit.CLASS: ContractModality.CLASS,
    ContractItemUnit.PACKAGE: ContractModality.LOT,
    ContractItemUnit.UST: ContractModality.UST,
    ContractItemUnit.HST: ContractModality.HST,
    ContractItemUnit.USN: ContractModality.USN,
}


@dataclass(frozen=True)
class IntelligenceRunResult:
    contract_id: int
    modality: str
    classified_items: int
    active_findings: int
    resolved_findings: int
    execution_id: int


def detect_item_modality(item):
    modality = UNIT_MODALITIES.get(item.unit, "")
    if modality:
        return modality, f"Unidade estruturada do item: {item.get_unit_display()}."
    return "", (
        "A unidade não é suficiente para classificar com segurança; "
        "é necessária confirmação humana baseada no Contrato e no TR."
    )


def _upsert_item_classification(item):
    modality, rationale = detect_item_modality(item)
    classification, created = ContractItemClassification.objects.get_or_create(
        item=item,
        defaults={
            "modality": modality,
            "rationale": rationale,
            "status": IntelligenceReviewStatus.DETECTED,
        },
    )
    if not created and classification.status not in (
        IntelligenceReviewStatus.CONFIRMED,
        IntelligenceReviewStatus.REJECTED,
        IntelligenceReviewStatus.SUPERSEDED,
        IntelligenceReviewStatus.INACTIVE,
    ):
        classification.modality = modality
        classification.rationale = rationale
        classification.status = (
            IntelligenceReviewStatus.DETECTED
            if modality
            else IntelligenceReviewStatus.AWAITING_CONFIRMATION
        )
        classification.save(
            update_fields=("modality", "rationale", "status", "updated_at")
        )
    return classification


def _upsert_contract_classification(contract, item_classifications):
    modalities = {item.modality for item in item_classifications if item.modality}
    if len(modalities) > 1:
        modality = ContractModality.MIXED
        rationale = "Itens estruturados indicam mais de uma modalidade."
    elif len(modalities) == 1:
        modality = next(iter(modalities))
        rationale = "Todos os itens classificáveis indicam a mesma modalidade."
    else:
        modality = ""
        rationale = (
            "Os dados estruturados atuais não bastam; confirme com base no Contrato e no TR."
        )
    classification, created = ContractClassification.objects.get_or_create(
        contract=contract,
        defaults={
            "modality": modality,
            "management_category": "",
            "rationale": rationale,
            "status": (
                IntelligenceReviewStatus.DETECTED
                if modality
                else IntelligenceReviewStatus.AWAITING_CONFIRMATION
            ),
        },
    )
    if not created and classification.status not in (
        IntelligenceReviewStatus.CONFIRMED,
        IntelligenceReviewStatus.REJECTED,
        IntelligenceReviewStatus.SUPERSEDED,
        IntelligenceReviewStatus.INACTIVE,
    ):
        classification.modality = modality
        classification.rationale = rationale
        classification.status = (
            IntelligenceReviewStatus.DETECTED
            if modality
            else IntelligenceReviewStatus.AWAITING_CONFIRMATION
        )
        classification.save(
            update_fields=("modality", "rationale", "status", "updated_at")
        )
    return classification


def _normalized_search_text(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(character.casefold() for character in normalized if character.isalnum())


def _contract_document_findings(contract):
    """Confere campos estruturados contra o PDF sem expor o conteúdo ao solicitante."""
    from documents.models import DocumentType

    document = contract.documents.filter(
        document_type=DocumentType.CONTRACT
    ).order_by("-version", "-uploaded_at", "-pk").first()
    if document is None:
        return [
            _finding_payload(
                fingerprint="ENGINE:CONTRACT_DOCUMENT_MISSING",
                code="CONTRACT_DOCUMENT_MISSING",
                severity=ContractFindingSeverity.INFO,
                title="Documento principal do contrato não localizado",
                explanation=(
                    "A conferência documental não foi executada porque não há arquivo "
                    "classificado como Contrato. Nenhum dado foi alterado."
                ),
                evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
            )
        ]
    if document.mime_type != "application/pdf":
        return [
            _finding_payload(
                fingerprint=f"ENGINE:CONTRACT_DOCUMENT_UNSUPPORTED:{document.pk}",
                code="CONTRACT_DOCUMENT_UNSUPPORTED",
                severity=ContractFindingSeverity.INFO,
                title="Formato do contrato ainda não analisável",
                explanation=(
                    "O motor preservou o arquivo privado, mas a leitura automática desta versão "
                    "aceita somente PDF com texto. A validação humana continua necessária."
                ),
                evidence=[{"tipo": "DOCUMENTO", "id": document.pk, "sha256": document.sha256}],
            )
        ]

    try:
        from pypdf import PdfReader

        document.file.open("rb")
        reader = PdfReader(document.file)
        text = "".join((page.extract_text() or "") for page in reader.pages[:60])[:300000]
    except Exception:
        return [
            _finding_payload(
                fingerprint=f"ENGINE:CONTRACT_DOCUMENT_UNREADABLE:{document.pk}",
                code="CONTRACT_DOCUMENT_UNREADABLE",
                severity=ContractFindingSeverity.INFO,
                title="PDF do contrato sem leitura automática",
                explanation=(
                    "O arquivo pode ser imagem, estar protegido ou não conter texto extraível. "
                    "O sistema não concluiu divergência e exige conferência humana."
                ),
                evidence=[{"tipo": "DOCUMENTO", "id": document.pk, "sha256": document.sha256}],
            )
        ]
    finally:
        try:
            document.file.close()
        except Exception:
            pass

    normalized_text = _normalized_search_text(text)
    if len(normalized_text) < 40:
        return [
            _finding_payload(
                fingerprint=f"ENGINE:CONTRACT_DOCUMENT_NO_TEXT:{document.pk}",
                code="CONTRACT_DOCUMENT_NO_TEXT",
                severity=ContractFindingSeverity.INFO,
                title="PDF do contrato sem texto suficiente",
                explanation=(
                    "Não foi possível comparar os campos cadastrados com segurança. "
                    "O sistema não tratou ausência de texto como erro contratual."
                ),
                evidence=[{"tipo": "DOCUMENTO", "id": document.pk, "sha256": document.sha256}],
            )
        ]

    findings = []
    for code, label, value in (
        ("NUMBER", "número do contrato", contract.number),
        ("PROCESS", "número do processo", contract.process_number),
        ("SUPPLIER", "nome da contratada", contract.supplier_name),
        ("SUPPLIER_TAX_ID", "CNPJ/CPF da contratada", contract.supplier_tax_id),
    ):
        searched = _normalized_search_text(value)
        if len(searched) >= 4 and searched not in normalized_text:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:CONTRACT_DOCUMENT_FIELD:{code}:{document.pk}",
                    code=f"CONTRACT_DOCUMENT_{code}_NOT_FOUND",
                    severity=ContractFindingSeverity.WARNING,
                    title=f"{label.capitalize()} não localizado no PDF",
                    explanation=(
                        f"O valor cadastrado para {label} não foi localizado no texto extraído. "
                        "Isso é uma notificação para conferência, não uma conclusão nem "
                        "uma correção automática."
                    ),
                    data={"campo": code, "valor_cadastrado": value},
                    evidence=[{"tipo": "DOCUMENTO", "id": document.pk, "sha256": document.sha256}],
                )
            )
    return findings


def _terms_of_reference_findings(contract):
    from documents.models import DocumentType

    document = contract.documents.filter(
        document_type=DocumentType.TERMS_OF_REFERENCE
    ).order_by("-version", "-uploaded_at", "-pk").first()
    if document is None:
        return [
            _finding_payload(
                fingerprint="ENGINE:TERMS_OF_REFERENCE_MISSING",
                code="TERMS_OF_REFERENCE_MISSING",
                severity=ContractFindingSeverity.INFO,
                title="Termo de Referência não localizado",
                explanation=(
                    "O motor analisou os dados estruturados disponíveis, mas não pode "
                    "confrontar regras com o TR sem uma fonte classificada e confirmada."
                ),
                evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
            )
        ]
    if document.mime_type != "application/pdf":
        return [
            _finding_payload(
                fingerprint=f"ENGINE:TERMS_OF_REFERENCE_UNSUPPORTED:{document.pk}",
                code="TERMS_OF_REFERENCE_UNSUPPORTED",
                severity=ContractFindingSeverity.INFO,
                title="Formato do TR ainda não analisável",
                explanation=(
                    "O TR foi localizado e preservado, mas a leitura automática desta etapa "
                    "aceita somente PDF com texto."
                ),
                evidence=[{"tipo": "DOCUMENTO", "id": document.pk, "sha256": document.sha256}],
            )
        ]
    return []


def _finding_payload(
    *, fingerprint, code, severity, title, explanation, data=None, evidence=None, rule=None
):
    return {
        "fingerprint": fingerprint,
        "code": code,
        "severity": severity,
        "title": title,
        "explanation": explanation,
        "data": data or {},
        "evidence": evidence or [],
        "rule": rule,
    }


def _detected_findings(contract, classification, item_classifications):
    findings = _contract_document_findings(contract) + _terms_of_reference_findings(contract)
    items = list(contract.items.filter(is_active=True))
    items_by_number = {}
    for item in items:
        normalized_number = " ".join(item.number.split()).casefold()
        items_by_number.setdefault(normalized_number, []).append(item)
    for duplicate_number, duplicate_items in items_by_number.items():
        if duplicate_number and len(duplicate_items) > 1:
            duplicate_ids = [item.pk for item in duplicate_items]
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:DUPLICATE_ITEM_NUMBER:{duplicate_number}",
                    code="DUPLICATE_ITEM_NUMBER",
                    severity=ContractFindingSeverity.WARNING,
                    title=f"Número de item repetido: {duplicate_items[0].number}",
                    explanation=(
                        "Dois ou mais itens ativos usam o mesmo número normalizado. "
                        "O sistema apenas sinalizou a duplicidade; o Fiscal deve conferir a fonte."
                    ),
                    data={"numero": duplicate_items[0].number, "itens": duplicate_ids},
                    evidence=[{"tipo": "ITEM", "id": item_id} for item_id in duplicate_ids],
                )
            )
    if items:
        item_total = sum((item.total_value for item in items), Decimal("0.00"))
        if item_total != contract.current_value:
            findings.append(
                _finding_payload(
                    fingerprint="ENGINE:ITEM_TOTAL_DIVERGENT",
                    code="ITEM_TOTAL_DIVERGENT",
                    severity=ContractFindingSeverity.WARNING,
                    title="Soma dos itens diverge do valor atual do contrato",
                    explanation=(
                        "A soma determinística de quantidade × valor unitário dos itens ativos "
                        "não coincide com o valor atual do contrato. O sistema não corrigiu nada."
                    ),
                    data={
                        "valor_contrato": str(contract.current_value),
                        "soma_itens": str(item_total),
                        "diferenca": str(contract.current_value - item_total),
                    },
                    evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
                )
            )
    if not classification.modality:
        findings.append(
            _finding_payload(
                fingerprint="ENGINE:CONTRACT_MODALITY_PENDING",
                code="CONTRACT_MODALITY_PENDING",
                severity=ContractFindingSeverity.INFO,
                title="Modalidade contratual pendente de confirmação",
                explanation=classification.rationale,
                evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
            )
        )
    for item_classification in item_classifications:
        if not item_classification.modality:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:ITEM_MODALITY_PENDING:{item_classification.item_id}",
                    code="ITEM_MODALITY_PENDING",
                    severity=ContractFindingSeverity.INFO,
                    title=f"Modalidade pendente no item {item_classification.item.number}",
                    explanation=item_classification.rationale,
                    evidence=[{"tipo": "ITEM", "id": item_classification.item_id}],
                )
            )
        elif item_classification.status == IntelligenceReviewStatus.CONFIRMED:
            detected_modality, detected_rationale = detect_item_modality(
                item_classification.item
            )
            if detected_modality and detected_modality != item_classification.modality:
                findings.append(
                    _finding_payload(
                        fingerprint=(
                            "ENGINE:ITEM_MODALITY_REVIEW:"
                            f"{item_classification.item_id}"
                        ),
                        code="ITEM_MODALITY_REVIEW",
                        severity=ContractFindingSeverity.WARNING,
                        title=(
                            "Modalidade confirmada difere da unidade estruturada no item "
                            f"{item_classification.item.number}"
                        ),
                        explanation=(
                            f"{detected_rationale} A modalidade confirmada foi "
                            f"{item_classification.get_modality_display()}. "
                            "A diferença exige conferência no Contrato/TR e não foi corrigida."
                        ),
                        data={
                            "modalidade_confirmada": item_classification.modality,
                            "modalidade_sugerida_pela_unidade": detected_modality,
                        },
                        evidence=[
                            {"tipo": "ITEM", "id": item_classification.item_id}
                        ],
                    )
                )

    try:
        contract_financial_position(contract)
    except NegativeBalanceError as error:
        findings.append(
            _finding_payload(
                fingerprint="ENGINE:NEGATIVE_FINANCIAL_BALANCE",
                code="NEGATIVE_FINANCIAL_BALANCE",
                severity=ContractFindingSeverity.CRITICAL,
                title="Saldo financeiro negativo",
                explanation=str(error),
                evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
            )
        )

    open_statuses = (
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.OPEN,
        WorkOrderStatus.SIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.SUSPENDED,
    )
    for work_order in contract.work_orders.filter(
        status__in=open_statuses,
        deadline__lt=timezone.localdate(),
    ):
        findings.append(
            _finding_payload(
                fingerprint=f"ENGINE:BR_TIC:OVERDUE_OS:{work_order.pk}",
                code="BR_TIC_OVERDUE_WORK_ORDER",
                severity=ContractFindingSeverity.WARNING,
                title=f"OS {work_order.number} com prazo vencido",
                explanation=(
                    "O pacote BR_TIC_FISCALIZATION identificou uma OS não encerrada após o prazo."
                ),
                data={"prazo": work_order.deadline.isoformat(), "status": work_order.status},
                evidence=[{"tipo": "ORDEM_SERVICO", "id": work_order.pk}],
            )
        )

    try:
        from .dashboard import build_contract_dashboard

        dashboard = build_contract_dashboard(contract)
    except NegativeBalanceError as error:
        findings.append(
            _finding_payload(
                fingerprint="ENGINE:OPERATIONAL_POSITION_NEGATIVE",
                code="OPERATIONAL_POSITION_NEGATIVE",
                severity=ContractFindingSeverity.CRITICAL,
                title="Saldo quantitativo ou financeiro operacional negativo",
                explanation=str(error),
                evidence=[{"tipo": "CONTRATO", "id": contract.pk}],
            )
        )
    else:
        for work_order in dashboard.work_orders_without_allocation:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:WORK_ORDER_WITHOUT_ALLOCATION:{work_order.pk}",
                    code="WORK_ORDER_WITHOUT_ALLOCATION",
                    severity=ContractFindingSeverity.WARNING,
                    title=f"OS {work_order.number} sem rateio ativo",
                    explanation=(
                        "A OS possui situação financeiramente efetiva, mas nenhum rateio ativo "
                        "foi localizado. A vinculação deve ser conferida pelo Fiscal."
                    ),
                    evidence=[{"tipo": "ORDEM_SERVICO", "id": work_order.pk}],
                )
            )
        for work_order in dashboard.completed_work_orders_without_invoice:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:COMPLETED_WITHOUT_INVOICE:{work_order.pk}",
                    code="COMPLETED_WITHOUT_INVOICE",
                    severity=ContractFindingSeverity.INFO,
                    title=f"OS {work_order.number} concluída sem Nota Fiscal",
                    explanation=(
                        "A OS está concluída e não possui Nota Fiscal ativa vinculada. "
                        "O alerta é informativo e não presume que o faturamento já seja devido."
                    ),
                    evidence=[{"tipo": "ORDEM_SERVICO", "id": work_order.pk}],
                )
            )
        for attention in (*dashboard.pending_invoices, *dashboard.divergent_invoices):
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:INVOICE_CHECK:{attention.invoice.pk}",
                    code="INVOICE_CHECK_PENDING",
                    severity=(
                        ContractFindingSeverity.CRITICAL
                        if attention in dashboard.divergent_invoices
                        else ContractFindingSeverity.WARNING
                    ),
                    title=f"NF {attention.invoice.number}/{attention.invoice.series}: {attention.status_label}",
                    explanation=(
                        "A conferência determinística da Nota Fiscal encontrou ponto que exige "
                        "revisão humana. Consulte o relatório da NF para cada evidência."
                    ),
                    data={"status_conferencia": attention.status},
                    evidence=[{"tipo": "NOTA_FISCAL", "id": attention.invoice.pk}],
                )
            )
        for alert in dashboard.low_commitments:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:LOW_COMMITMENT_BALANCE:{alert.commitment.pk}",
                    code="LOW_COMMITMENT_BALANCE",
                    severity=ContractFindingSeverity.WARNING,
                    title=f"Saldo do empenho {alert.commitment.number} abaixo de 20%",
                    explanation=(
                        "O saldo disponível do empenho atingiu o limite de atenção já adotado "
                        "pelo painel do sistema."
                    ),
                    data={"saldo": str(alert.available), "percentual": str(alert.percentage)},
                    evidence=[{"tipo": "EMPENHO", "id": alert.commitment.pk}],
                )
            )
        for alert in dashboard.low_hour_items:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:LOW_HOUR_BALANCE:{alert.item.pk}",
                    code="LOW_HOUR_BALANCE",
                    severity=ContractFindingSeverity.WARNING,
                    title=f"Saldo de horas do item {alert.item.number} abaixo de 20%",
                    explanation=(
                        "O saldo quantitativo de horas atingiu o limite de atenção já adotado "
                        "pelo painel do sistema."
                    ),
                    data={"saldo_horas": str(alert.available), "percentual": str(alert.percentage)},
                    evidence=[{"tipo": "ITEM", "id": alert.item.pk}],
                )
            )

    for rule in contract.intelligence_rules.filter(
        status=IntelligenceReviewStatus.CONFIRMED,
        rule_type=ContractRuleType.CALCULATION,
    ):
        if rule.calculator_key not in ALLOWED_CALCULATORS:
            findings.append(
                _finding_payload(
                    fingerprint=f"ENGINE:UNSUPPORTED_CALCULATOR:{rule.pk}",
                    code="UNSUPPORTED_CALCULATOR",
                    severity=ContractFindingSeverity.CRITICAL,
                    title=f"Regra {rule.code} sem calculadora permitida",
                    explanation=(
                        "A regra confirmada referencia uma fórmula não implementada de forma tipada; "
                        "nenhum cálculo oficial foi produzido."
                    ),
                    evidence=[{"tipo": "REGRA", "id": rule.pk}],
                    rule=rule,
                )
            )
    return findings


def _persist_findings(contract, actor, detected):
    seen = set()
    for payload in detected:
        fingerprint = payload.pop("fingerprint")
        seen.add(fingerprint)
        finding, created = ContractFinding.objects.get_or_create(
            contract=contract,
            fingerprint=fingerprint,
            defaults=payload,
        )
        if not created:
            previous_status = finding.status
            finding.code = payload["code"]
            finding.severity = payload["severity"]
            finding.title = payload["title"]
            finding.explanation = payload["explanation"]
            finding.data = payload["data"]
            finding.evidence = payload["evidence"]
            finding.rule = payload["rule"]
            if finding.status == ContractFindingStatus.RESOLVED:
                finding.status = ContractFindingStatus.NEW
                finding.resolved_by = None
                finding.resolved_at = None
                finding.resolution_justification = ""
            finding.save()
            if previous_status == ContractFindingStatus.RESOLVED:
                ContractIntelligenceEvent.objects.create(
                    event_type=ContractIntelligenceEvent.EventType.FINDING_REOPENED,
                    contract=contract,
                    actor=actor,
                    finding=finding,
                    details={"status_anterior": previous_status, "status_novo": finding.status},
                )
        else:
            ContractIntelligenceEvent.objects.create(
                event_type=ContractIntelligenceEvent.EventType.FINDING_CREATED,
                contract=contract,
                actor=actor,
                finding=finding,
                details={"codigo": finding.code, "gravidade": finding.severity},
            )

    resolved = 0
    stale = contract.intelligence_findings.filter(
        fingerprint__startswith="ENGINE:",
        status__in=ACTIVE_FINDING_STATUSES,
    ).exclude(fingerprint__in=seen)
    now = timezone.now()
    for finding in stale:
        finding.status = ContractFindingStatus.RESOLVED
        finding.resolved_by = actor
        finding.resolved_at = now
        finding.resolution_justification = (
            "Reprocessamento determinístico: a condição não foi encontrada."
        )
        finding.save(
            update_fields=(
                "status",
                "resolved_by",
                "resolved_at",
                "resolution_justification",
            )
        )
        ContractIntelligenceEvent.objects.create(
            event_type=ContractIntelligenceEvent.EventType.FINDING_AUTO_RESOLVED,
            contract=contract,
            actor=actor,
            finding=finding,
            details={"justificativa": finding.resolution_justification},
        )
        resolved += 1
    return resolved


@transaction.atomic
def run_contract_intelligence(*, contract_id, actor, reason="execucao_manual"):
    contract = contracts_scannable_by(actor).select_for_update().get(pk=contract_id)
    item_classifications = [
        _upsert_item_classification(item)
        for item in contract.items.filter(is_active=True).order_by("number", "pk")
    ]
    classification = _upsert_contract_classification(contract, item_classifications)
    detected = _detected_findings(contract, classification, item_classifications)
    resolved = _persist_findings(contract, actor, detected)
    active_count = contract.intelligence_findings.filter(
        status__in=ACTIVE_FINDING_STATUSES
    ).count()
    summary = {
        "modalidade": classification.modality,
        "itens_classificados": len(item_classifications),
        "pendencias_ativas": active_count,
        "pendencias_resolvidas_no_reprocessamento": resolved,
        "rule_pack": BR_TIC_FISCALIZATION,
    }
    execution = IntelligenceExecution.objects.create(
        contract=contract,
        executed_by=actor,
        reason=reason,
        summary=summary,
    )
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.ENGINE_EXECUTED,
        contract=contract,
        actor=actor,
        classification=classification,
        execution=execution,
        details=summary,
    )
    return IntelligenceRunResult(
        contract_id=contract.pk,
        modality=classification.modality,
        classified_items=len(item_classifications),
        active_findings=active_count,
        resolved_findings=resolved,
        execution_id=execution.pk,
    )


@transaction.atomic
def confirm_contract_classification(*, contract_id, actor, modality, management_category):
    if modality not in ContractModality.values:
        raise ValidationError("Modalidade contratual inválida.")
    if management_category not in ContractManagementCategory.values:
        raise ValidationError("Categoria gerencial inválida.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    classification, _ = ContractClassification.objects.select_for_update().get_or_create(
        contract=contract
    )
    classification.modality = modality
    classification.management_category = management_category
    classification.status = IntelligenceReviewStatus.CONFIRMED
    classification.confirmed_by = actor
    classification.confirmed_at = timezone.now()
    classification.save()
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.CLASSIFICATION_CONFIRMED,
        contract=contract,
        actor=actor,
        classification=classification,
        details={
            "modalidade": modality,
            "categoria_gerencial": management_category,
            "versao": classification.version,
        },
    )
    return classification


@transaction.atomic
def confirm_item_classification(*, contract_id, item_id, actor, modality):
    if modality not in ContractModality.values:
        raise ValidationError("Modalidade do item inválida.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    item = contract.items.select_for_update().get(pk=item_id, is_active=True)
    classification, _ = ContractItemClassification.objects.select_for_update().get_or_create(
        item=item
    )
    changed = (
        classification.status == IntelligenceReviewStatus.CONFIRMED
        and classification.modality != modality
    )
    if changed:
        classification.version += 1
    classification.modality = modality
    classification.status = IntelligenceReviewStatus.CONFIRMED
    classification.rationale = (
        "Modalidade confirmada pelo Fiscal com base na documentação contratual."
    )
    classification.confirmed_by = actor
    classification.confirmed_at = timezone.now()
    classification.save()
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.CLASSIFICATION_CONFIRMED,
        contract=contract,
        actor=actor,
        details={
            "escopo": "item",
            "item_id": item.pk,
            "modalidade": modality,
            "versao": classification.version,
        },
    )
    return classification


@transaction.atomic
def create_contract_clause_candidate(
    *, contract_id, actor, clause_type, source_document, source_reference, excerpt
):
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    if clause_type not in ContractClauseType.values:
        raise ValidationError("Tipo de cláusula inválido.")
    if not source_document or source_document.contract_id != contract.pk:
        raise ValidationError("O documento fonte deve pertencer ao contrato.")
    source_reference = " ".join((source_reference or "").split())
    excerpt = " ".join((excerpt or "").split())
    if not source_reference or not excerpt:
        raise ValidationError("Informe a cláusula/página e o trecho de evidência.")
    clause = ContractClause.objects.create(
        contract=contract,
        clause_type=clause_type,
        source_document=source_document,
        source_reference=source_reference,
        excerpt=excerpt,
        status=IntelligenceReviewStatus.AWAITING_CONFIRMATION,
    )
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.CLAUSE_CREATED,
        contract=contract,
        actor=actor,
        details={
            "clausula_id": clause.pk,
            "tipo": clause.clause_type,
            "documento_id": source_document.pk,
            "referencia": source_reference,
        },
    )
    return clause


@transaction.atomic
def review_contract_clause(*, clause_id, actor, action):
    clause = ContractClause.objects.select_for_update().select_related("contract").get(
        pk=clause_id
    )
    if not contracts_writable_by(actor).filter(pk=clause.contract_id).exists():
        raise PermissionDenied("Somente o Fiscal autorizado pode revisar esta cláusula.")
    if action == "confirm":
        clause.status = IntelligenceReviewStatus.CONFIRMED
    elif action == "reject":
        clause.status = IntelligenceReviewStatus.REJECTED
    else:
        raise ValidationError("Ação de revisão de cláusula inválida.")
    clause.confirmed_by = actor
    clause.confirmed_at = timezone.now()
    clause.save(update_fields=("status", "confirmed_by", "confirmed_at"))
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.CLAUSE_REVIEWED,
        contract=clause.contract,
        actor=actor,
        details={"clausula_id": clause.pk, "acao": action, "status": clause.status},
    )
    return clause


@transaction.atomic
def create_contract_rule_candidate(
    *, contract_id, actor, code, name, description, rule_type,
    source_document, source_reference, calculator_key="", formula_description=""
):
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    if rule_type not in ContractRuleType.values:
        raise ValidationError("Tipo de regra inválido.")
    if not source_document or source_document.contract_id != contract.pk:
        raise ValidationError("O documento fonte deve pertencer ao contrato.")
    code = "_".join((code or "").strip().upper().split())
    name = " ".join((name or "").split())
    description = " ".join((description or "").split())
    source_reference = " ".join((source_reference or "").split())
    formula_description = " ".join((formula_description or "").split())
    if not all((code, name, description, source_reference)):
        raise ValidationError("Preencha ID, nome, descrição e fonte da regra.")
    if rule_type == ContractRuleType.CALCULATION:
        if calculator_key not in ALLOWED_CALCULATORS or not formula_description:
            raise ValidationError("Regra de cálculo exige calculadora tipada e fórmula.")
    else:
        calculator_key = ""
    latest = contract.intelligence_rules.filter(code=code).order_by("-version", "-pk").first()
    version = (latest.version + 1) if latest else 1
    rule = ContractRule.objects.create(
        contract=contract,
        code=code,
        name=name,
        description=description,
        rule_type=rule_type,
        source_document=source_document,
        source_reference=source_reference,
        calculator_key=calculator_key,
        formula_description=formula_description,
        status=IntelligenceReviewStatus.AWAITING_CONFIRMATION,
        version=version,
        supersedes=latest,
    )
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.RULE_CREATED,
        contract=contract,
        actor=actor,
        rule=rule,
        details={
            "codigo": rule.code,
            "versao": rule.version,
            "documento_id": source_document.pk,
            "referencia": source_reference,
        },
    )
    return rule


@transaction.atomic
def review_contract_rule(*, rule_id, actor, action):
    rule = ContractRule.objects.select_for_update().select_related("contract").get(pk=rule_id)
    if not contracts_writable_by(actor).filter(pk=rule.contract_id).exists():
        raise PermissionDenied("Somente o Fiscal autorizado pode revisar esta regra.")
    if action == "confirm":
        if not rule.source_document_id or not rule.source_reference:
            raise ValidationError("Regra sem documento e cláusula não pode ser confirmada.")
        if rule.rule_type == ContractRuleType.CALCULATION:
            if rule.calculator_key not in ALLOWED_CALCULATORS:
                raise ValidationError("A regra não possui calculadora tipada permitida.")
            if not rule.formula_description:
                raise ValidationError("A regra não possui fórmula explicável.")
        rule.status = IntelligenceReviewStatus.CONFIRMED
        rule.confirmed_by = actor
        rule.confirmed_at = timezone.now()
        if rule.supersedes_id:
            ContractRule.objects.filter(pk=rule.supersedes_id).update(
                status=IntelligenceReviewStatus.SUPERSEDED
            )
    elif action == "reject":
        rule.status = IntelligenceReviewStatus.REJECTED
        rule.confirmed_by = actor
        rule.confirmed_at = timezone.now()
    else:
        raise ValidationError("Ação de revisão de regra inválida.")
    rule.save()
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.RULE_REVIEWED,
        contract=rule.contract,
        actor=actor,
        rule=rule,
        details={"acao": action, "status": rule.status, "versao": rule.version},
    )
    return rule


def calculate_with_confirmed_rule(*, rule, quantity, unit_value):
    if rule.status != IntelligenceReviewStatus.CONFIRMED:
        raise ValidationError("Regra não confirmada não produz cálculo oficial.")
    if rule.calculator_key != CALCULATOR_QUANTITY_X_UNIT_VALUE:
        raise ValidationError("A regra não possui calculadora determinística disponível.")
    if not isinstance(quantity, Decimal) or not isinstance(unit_value, Decimal):
        raise TypeError("Quantidade e valor unitário devem usar Decimal.")
    value = calculate_item_total(quantity, unit_value)
    return {
        "valor": value,
        "formula": "quantidade × valor unitário",
        "dados": {"quantidade": str(quantity), "valor_unitario": str(unit_value)},
        "regra": {
            "id": rule.pk,
            "codigo": rule.code,
            "versao": rule.version,
            "documento": rule.source_document_id,
            "clausula": rule.source_reference,
        },
    }


def serialize_calculation(result):
    return {
        "valor": str(result.value),
        "evidencias": [
            {
                "tipo": item.source_type,
                "id": item.source_id,
                "descricao": item.description,
                "valor": str(item.value),
                "operacao": item.operation,
            }
            for item in result.evidence
        ],
    }


def financial_explanation(contract):
    position = contract_financial_position(contract)
    return {
        "valor_atual": str(contract.current_value),
        "empenhado": serialize_calculation(position.total_committed_budget),
        "comprometido": serialize_calculation(position.committed_value),
        "executado": serialize_calculation(position.executed_value),
        "faturado": serialize_calculation(position.invoiced_gross_value),
        "pago": serialize_calculation(position.paid_value),
        "saldo_contratual": serialize_calculation(position.contract_balance),
    }


@transaction.atomic
def transition_finding(*, finding_id, actor, status, justification=""):
    finding = ContractFinding.objects.select_for_update().select_related("contract").get(
        pk=finding_id
    )
    if not contracts_visible_to(actor).filter(pk=finding.contract_id).exists():
        raise PermissionDenied("Achado não autorizado.")
    if not contracts_writable_by(actor).filter(pk=finding.contract_id).exists():
        raise PermissionDenied("Somente o Fiscal autorizado pode tratar este achado.")
    previous_status = finding.status
    if status == ContractFindingStatus.READ:
        finding.status = status
        finding.read_by = actor
        finding.read_at = timezone.now()
        finding.save(update_fields=("status", "read_by", "read_at"))
        ContractIntelligenceEvent.objects.create(
            event_type=ContractIntelligenceEvent.EventType.FINDING_TRANSITIONED,
            contract=finding.contract,
            actor=actor,
            finding=finding,
            details={"status_anterior": previous_status, "status_novo": status},
        )
        return finding
    if status not in (
        ContractFindingStatus.IN_ANALYSIS,
        ContractFindingStatus.AWAITING_INFORMATION,
        ContractFindingStatus.RESOLVED,
        ContractFindingStatus.DISCARDED,
    ):
        raise ValidationError("Transição de achado inválida.")
    justification = " ".join((justification or "").split())
    if status == ContractFindingStatus.DISCARDED and not justification:
        raise ValidationError("Descarte exige justificativa.")
    finding.status = status
    if status in (ContractFindingStatus.RESOLVED, ContractFindingStatus.DISCARDED):
        finding.resolved_by = actor
        finding.resolved_at = timezone.now()
        finding.resolution_justification = justification
    finding.save()
    ContractIntelligenceEvent.objects.create(
        event_type=ContractIntelligenceEvent.EventType.FINDING_TRANSITIONED,
        contract=finding.contract,
        actor=actor,
        finding=finding,
        details={
            "status_anterior": previous_status,
            "status_novo": status,
            "justificativa": justification,
        },
    )
    return finding


def contract_intelligence_snapshot(contract):
    classification = getattr(contract, "intelligence_classification", None)
    active_findings = contract.intelligence_findings.filter(
        status__in=ACTIVE_FINDING_STATUSES
    )
    try:
        financial = financial_explanation(contract)
        financial_error = ""
    except NegativeBalanceError as error:
        financial = {}
        financial_error = str(error)
    items = []
    for item in contract.items.filter(is_active=True).order_by("number", "pk")[:30]:
        item_classification = getattr(item, "intelligence_classification", None)
        try:
            position = item_financial_position(item)
            position_data = {
                "quantidade_utilizada": str(position.used_quantity.value),
                "saldo_quantitativo": str(position.quantity_balance.value),
                "valor_utilizado": str(position.used_value.value),
                "saldo_financeiro": str(position.financial_balance.value),
            }
        except NegativeBalanceError as error:
            position_data = {"erro": str(error)}
        items.append({
            "id": item.pk,
            "numero": item.number,
            "descricao": item.description,
            "unidade": item.unit_display,
            "quantidade_contratada": str(item.contracted_quantity),
            "valor_unitario": str(item.unit_value),
            "modalidade": item_classification.modality if item_classification else "",
            **position_data,
        })
    open_statuses = (
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.OPEN,
        WorkOrderStatus.SIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.SUSPENDED,
    )
    open_work_orders = list(
        contract.work_orders.filter(status__in=open_statuses)
        .order_by("deadline", "number", "pk")
        .values("id", "number", "status", "deadline", "hours", "quantity")[:30]
    )
    for work_order in open_work_orders:
        for field in ("deadline", "hours", "quantity"):
            if work_order[field] is not None:
                work_order[field] = str(work_order[field])
    from documents.models import DocumentType

    source_types = set(
        contract.documents.filter(
            document_type__in=(DocumentType.CONTRACT, DocumentType.TERMS_OF_REFERENCE)
        ).values_list("document_type", flat=True)
    )
    return {
        "contrato": {
            "id": contract.pk,
            "numero": contract.number,
            "processo": contract.process_number,
            "contratada": contract.supplier_name,
            "vigencia_inicio": contract.validity_start.isoformat(),
            "vigencia_fim": contract.validity_end.isoformat(),
            "status": contract.status,
        },
        "classificacao": {
            "modalidade": classification.modality if classification else "",
            "categoria_gerencial": (
                classification.management_category if classification else ""
            ),
            "status": classification.status if classification else "NAO_EXECUTADA",
            "fundamentacao": classification.rationale if classification else "",
        },
        "financeiro": financial,
        "erro_financeiro": financial_error,
        "itens": items,
        "ordens_servico_abertas": open_work_orders,
        "fontes_prioritarias": {
            "contrato": DocumentType.CONTRACT in source_types,
            "termo_referencia": DocumentType.TERMS_OF_REFERENCE in source_types,
        },
        "regras_confirmadas": list(
            contract.intelligence_rules.filter(
                status=IntelligenceReviewStatus.CONFIRMED
            ).values("id", "code", "name", "rule_type", "source_reference", "version")
        ),
        "pendencias_ativas": list(
            active_findings.values(
                "id", "code", "severity", "status", "title", "explanation", "data"
            )[:20]
        ),
    }
