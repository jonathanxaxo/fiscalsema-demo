"""Serviços de governança contratual com confirmação humana e trilha auditável."""

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile

from .models import (
    ChecklistApplicability,
    ChecklistStatus,
    Contract,
    ContractAlertPolicy,
    ContractChange,
    ContractChangeStatus,
    ContractChecklistItem,
    ContractEvent,
    ContractExternalRecord,
    ContractObligation,
    ContractReceipt,
    ContractRisk,
)
from .services import contracts_visible_to, contracts_writable_by


@dataclass(frozen=True)
class ControlPack:
    code: str
    title: str
    description: str
    items: tuple


COMMON_SOURCE = "Contrato, Termo de Referência e norma aplicável — confirmar no caso concreto."
TIC_NORMATIVE_SOURCE = (
    "IN Conjunta 001/2024/SEPLAG/CGE, com alterações da IN Conjunta "
    "001/2025/SEPLAG/CGE, e Contrato/TR — confirmar aplicabilidade e versão vigente."
)

CONTROL_PACKS = {
    "TIC": ControlPack(
        code="TIC",
        title="Tecnologia da Informação e Comunicação",
        description="Planejamento, execução, qualidade, segurança e transferência de conhecimento.",
        items=(
            ("TIC-01", "Artefatos de planejamento conferidos", "Conferir DFD, ETP, TR e aprovações exigidas para a contratação.", "IN 008/2022/SEPLAG e documentos oficiais do processo — confirmar aplicabilidade."),
            ("TIC-02", "Mapa de riscos atualizado", "Identificar riscos, responsáveis, respostas e periodicidade de revisão.", COMMON_SOURCE),
            ("TIC-03", "OS ou instrumento de demanda vinculado", "Vincular escopo, prazo, responsáveis, métrica e entregáveis à demanda autorizada.", COMMON_SOURCE),
            ("TIC-04", "Métrica e memória de cálculo confirmadas", "Confirmar HST, UST, USN, ponto de função, sprint, hora ou entregável conforme a fonte.", TIC_NORMATIVE_SOURCE),
            ("TIC-05", "SLA, IMR e qualidade acompanhados", "Conferir indicadores, níveis mínimos, glosas e evidências de qualidade aplicáveis.", COMMON_SOURCE),
            ("TIC-06", "Segurança, LGPD e sigilo conferidos", "Conferir obrigações de segurança, privacidade, confidencialidade e resposta a incidentes.", COMMON_SOURCE),
            ("TIC-07", "Conhecimento e documentação transferidos", "Conferir documentação técnica, treinamento e transferência de conhecimento previstos.", TIC_NORMATIVE_SOURCE),
            ("TIC-08", "Propriedade intelectual e código-fonte conferidos", "Verificar direitos, repositórios, versões e entrega de artefatos quando previstos.", COMMON_SOURCE),
            ("TIC-09", "Recebimentos e homologação registrados", "Registrar recebimento provisório, aceite técnico, homologação e recebimento definitivo aplicáveis.", "Lei 14.133/2021, art. 140, e Contrato/TR."),
        ),
    ),
    "BENS_EQUIPAMENTOS": ControlPack(
        code="BENS_EQUIPAMENTOS",
        title="Bens e equipamentos",
        description="Entrega, conferência, identificação, garantia e recebimento.",
        items=(
            ("BEM-01", "Itens, quantidades e especificações conferidos", "Comparar o material entregue com o instrumento contratual.", COMMON_SOURCE),
            ("BEM-02", "Entrega e inspeção registradas", "Registrar data, local, responsável e resultado da inspeção.", COMMON_SOURCE),
            ("BEM-03", "Série, patrimônio ou identificação registrados", "Controlar identificação individual quando aplicável.", COMMON_SOURCE),
            ("BEM-04", "Garantia e assistência acompanhadas", "Registrar prazo, cobertura e acionamentos de garantia quando previstos.", COMMON_SOURCE),
            ("BEM-05", "Recebimentos provisório e definitivo registrados", "Registrar os termos e eventual rejeição ou substituição.", "Lei 14.133/2021, art. 140, e Contrato/TR."),
        ),
    ),
    "SERVICOS_CONTINUADOS": ControlPack(
        code="SERVICOS_CONTINUADOS",
        title="Serviços continuados",
        description="Medição periódica, níveis de serviço, obrigações e reajustes.",
        items=(
            ("SER-01", "Medição periódica conferida", "Vincular período, quantidade, resultado, evidências e responsável.", COMMON_SOURCE),
            ("SER-02", "Níveis de serviço acompanhados", "Conferir indicadores, ocorrências, glosas e correções previstas.", COMMON_SOURCE),
            ("SER-03", "Obrigações específicas verificadas", "Conferir obrigações trabalhistas e documentais somente quando aplicáveis.", COMMON_SOURCE),
            ("SER-04", "Reajuste ou repactuação controlados", "Registrar data-base, fonte, cálculo e instrumento formal aplicável.", "Lei 14.133/2021, arts. 92, 135 e 136, e Contrato/TR."),
            ("SER-05", "Recebimento e faturamento conciliados", "Conferir medição, aceite, nota fiscal e pagamento.", COMMON_SOURCE),
        ),
    ),
    "OBRAS_ENGENHARIA": ControlPack(
        code="OBRAS_ENGENHARIA",
        title="Obras e serviços de engenharia",
        description="Cronograma, medições, responsabilidade técnica e evidências de campo.",
        items=(
            ("OBR-01", "Cronograma físico-financeiro acompanhado", "Conferir etapas previstas, executadas, medidas e pagas.", COMMON_SOURCE),
            ("OBR-02", "Responsabilidade técnica conferida", "Registrar referências dos responsáveis e documentos técnicos exigidos.", COMMON_SOURCE),
            ("OBR-03", "Licenças e autorizações acompanhadas", "Controlar somente as licenças e autorizações aplicáveis ao objeto.", COMMON_SOURCE),
            ("OBR-04", "Boletins e evidências de medição registrados", "Vincular medições, memória de cálculo e evidências de campo.", COMMON_SOURCE),
            ("OBR-05", "Alterações de projeto formalizadas", "Conferir justificativa, autorização, limites e termo formal antes da execução.", "Lei 14.133/2021, arts. 124 a 136, e processo oficial."),
            ("OBR-06", "Recebimentos provisório e definitivo registrados", "Registrar termos detalhados e pendências de correção.", "Lei 14.133/2021, art. 140, e Contrato/TR."),
        ),
    ),
    "LICENCAS_ASSINATURAS": ControlPack(
        code="LICENCAS_ASSINATURAS",
        title="Licenças, assinaturas e serviços recorrentes",
        description="Quantidade licenciada, consumo, suporte, continuidade e prorrogação formal.",
        items=(
            ("LIC-01", "Licenças e usuários conciliados", "Conferir quantidade contratada, ativada e efetivamente utilizada.", COMMON_SOURCE),
            ("LIC-02", "Vigência e continuidade acompanhadas", "Alertar sobre prazo, suporte e risco de descontinuidade.", COMMON_SOURCE),
            ("LIC-03", "Suporte e níveis de serviço conferidos", "Registrar chamados, prazos e resultados quando previstos.", COMMON_SOURCE),
            ("LIC-04", "Reajuste e prorrogação formalizados", "Registrar análise e instrumento oficial; não presumir renovação automática.", "Lei 14.133/2021, art. 107, e Contrato/TR."),
        ),
    ),
    "ENTREGA_UNICA": ControlPack(
        code="ENTREGA_UNICA",
        title="Entrega única",
        description="Prazo, quantidade, inspeção, correção e recebimento.",
        items=(
            ("ENT-01", "Prazo e local de entrega confirmados", "Conferir os dados na fonte oficial.", COMMON_SOURCE),
            ("ENT-02", "Quantidade e conformidade inspecionadas", "Registrar resultado, responsável e evidências da inspeção.", COMMON_SOURCE),
            ("ENT-03", "Pendências, substituições ou rejeições registradas", "Registrar correções sem alterar silenciosamente o objeto recebido.", COMMON_SOURCE),
            ("ENT-04", "Recebimento definitivo registrado", "Vincular o termo detalhado e a decisão humana competente.", "Lei 14.133/2021, art. 140, e Contrato/TR."),
        ),
    ),
}


def _visible_contract(contract_id, actor):
    try:
        return contracts_visible_to(actor).get(pk=contract_id)
    except Contract.DoesNotExist as exc:
        raise PermissionDenied("Contrato fora do escopo autorizado.") from exc


def _writable_contract(contract_id, actor):
    try:
        return contracts_writable_by(actor).get(pk=contract_id)
    except Contract.DoesNotExist as exc:
        raise PermissionDenied("Somente o Fiscal autorizado pode alterar a governança.") from exc


def governance_snapshot(contract, actor):
    _visible_contract(contract.pk, actor)
    classification = getattr(contract, "intelligence_classification", None)
    category = classification.management_category if classification else ""
    recommendation = {
        "SISTEMA": "TIC",
        "EQUIPAMENTO": "BENS_EQUIPAMENTOS",
        "SERVICO_CONTINUO": "SERVICOS_CONTINUADOS",
        "OBRA": "OBRAS_ENGENHARIA",
        "LICENCA": "LICENCAS_ASSINATURAS",
        "ENTREGA_UNICA": "ENTREGA_UNICA",
    }.get(category)
    limited_auxiliary = actor.profile == UserProfile.AUXILIARY_ADMINISTRATIVE
    return {
        "policy": getattr(contract, "alert_policy", None),
        "obligations": contract.obligations.filter(
            category__in=("ADMINISTRATIVA", "DOCUMENTAL")
        ) if limited_auxiliary else contract.obligations.all(),
        "changes": contract.changes.none() if limited_auxiliary else contract.changes.all(),
        "receipts": contract.receipts.none() if limited_auxiliary else contract.receipts.all(),
        "risks": contract.risks.none() if limited_auxiliary else contract.risks.all(),
        "checklist_items": (
            contract.checklist_items.none() if limited_auxiliary else contract.checklist_items.all()
        ),
        "external_records": contract.external_records.all(),
        "packs": () if limited_auxiliary else CONTROL_PACKS.values(),
        "recommended_pack": recommendation,
        "can_edit": contracts_writable_by(actor).filter(pk=contract.pk).exists(),
        "limited_auxiliary": limited_auxiliary,
    }


@transaction.atomic
def update_alert_policy(*, contract_id, actor, days):
    contract = _writable_contract(contract_id, actor)
    policy, _ = ContractAlertPolicy.objects.select_for_update().get_or_create(
        contract=contract,
        defaults={"updated_by": actor, "validity_warning_days": days},
    )
    policy.validity_warning_days = days
    policy.updated_by = actor
    policy.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.ALERT_POLICY_UPDATED,
        contract=contract,
        actor=actor,
        details={"validity_warning_days": policy.validity_warning_days},
    )
    return policy


@transaction.atomic
def create_obligation(*, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    obligation = ContractObligation(contract=contract, created_by=actor, **data)
    obligation.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.OBLIGATION_CREATED,
        contract=contract,
        actor=actor,
        details={"obligation_id": obligation.pk},
    )
    return obligation


@transaction.atomic
def update_obligation(*, obligation_id, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    obligation = ContractObligation.objects.select_for_update().get(
        pk=obligation_id, contract=contract
    )
    for field, value in data.items():
        setattr(obligation, field, value)
    obligation.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.OBLIGATION_UPDATED,
        contract=contract,
        actor=actor,
        details={"obligation_id": obligation.pk, "status": obligation.status},
    )
    return obligation


@transaction.atomic
def create_contract_change(*, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    change = ContractChange(contract=contract, created_by=actor, **data)
    change.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CHANGE_CREATED,
        contract=contract,
        actor=actor,
        details={"change_id": change.pk, "type": change.change_type},
    )
    return change


@transaction.atomic
def void_contract_change(*, change_id, contract_id, actor, reason):
    contract = _writable_contract(contract_id, actor)
    change = ContractChange.objects.select_for_update().get(pk=change_id, contract=contract)
    if change.status == ContractChangeStatus.VOIDED:
        raise ValidationError("A alteração já está anulada.")
    change.status = ContractChangeStatus.VOIDED
    change.void_reason = reason
    change.voided_by = actor
    change.voided_at = timezone.now()
    change.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CHANGE_VOIDED,
        contract=contract,
        actor=actor,
        details={"change_id": change.pk},
    )
    return change


@transaction.atomic
def create_receipt(*, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    receipt = ContractReceipt(contract=contract, recorded_by=actor, **data)
    receipt.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.RECEIPT_CREATED,
        contract=contract,
        actor=actor,
        details={"receipt_id": receipt.pk, "type": receipt.receipt_type},
    )
    return receipt


@transaction.atomic
def create_risk(*, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    risk = ContractRisk(contract=contract, created_by=actor, **data)
    risk.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.RISK_CREATED,
        contract=contract,
        actor=actor,
        details={"risk_id": risk.pk},
    )
    return risk


@transaction.atomic
def update_risk(*, risk_id, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    risk = ContractRisk.objects.select_for_update().get(pk=risk_id, contract=contract)
    for field, value in data.items():
        setattr(risk, field, value)
    risk.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.RISK_UPDATED,
        contract=contract,
        actor=actor,
        details={"risk_id": risk.pk, "status": risk.status},
    )
    return risk


@transaction.atomic
def apply_control_pack(*, contract_id, actor, pack_code):
    contract = _writable_contract(contract_id, actor)
    try:
        pack = CONTROL_PACKS[pack_code]
    except KeyError as exc:
        raise ValidationError("Pacote de controle desconhecido.") from exc
    created = 0
    for code, title, guidance, source in pack.items:
        _, was_created = ContractChecklistItem.objects.get_or_create(
            contract=contract,
            pack_code=pack.code,
            code=code,
            defaults={
                "title": title,
                "guidance": guidance,
                "source_reference": source,
                "applicability": ChecklistApplicability.TO_CONFIRM,
                "status": ChecklistStatus.PENDING,
                "created_by": actor,
            },
        )
        created += int(was_created)
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.PACK_APPLIED,
        contract=contract,
        actor=actor,
        details={"pack_code": pack.code, "created_items": created},
    )
    return pack, created


@transaction.atomic
def update_checklist_item(*, item_id, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    item = ContractChecklistItem.objects.select_for_update().get(
        pk=item_id, contract=contract
    )
    for field, value in data.items():
        setattr(item, field, value)
    item.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CHECKLIST_UPDATED,
        contract=contract,
        actor=actor,
        details={"checklist_item_id": item.pk, "status": item.status},
    )
    return item


@transaction.atomic
def create_external_record(*, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    record = ContractExternalRecord(contract=contract, updated_by=actor, **data)
    record.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.EXTERNAL_RECORD_CREATED,
        contract=contract,
        actor=actor,
        details={"external_record_id": record.pk, "system": record.system},
    )
    return record


@transaction.atomic
def update_external_record(*, record_id, contract_id, actor, data):
    contract = _writable_contract(contract_id, actor)
    record = ContractExternalRecord.objects.select_for_update().get(
        pk=record_id, contract=contract
    )
    for field, value in data.items():
        setattr(record, field, value)
    record.updated_by = actor
    record.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.EXTERNAL_RECORD_UPDATED,
        contract=contract,
        actor=actor,
        details={"external_record_id": record.pk, "system": record.system},
    )
    return record


def contract_governance_counts(contract, *, auxiliary=False):
    today = timezone.localdate()
    obligations = contract.obligations.all()
    if auxiliary:
        obligations = obligations.filter(category__in=("ADMINISTRATIVA", "DOCUMENTAL"))
    return {
        "open_obligations": obligations.exclude(
            status__in=("CONCLUIDA", "DISPENSADA")
        ).count(),
        "overdue_obligations": obligations.exclude(
            status__in=("CONCLUIDA", "DISPENSADA")
        ).filter(due_date__lt=today).count(),
        "open_risks": 0 if auxiliary else contract.risks.exclude(status="ENCERRADO").count(),
        "pending_checklist": (
            0 if auxiliary else contract.checklist_items.filter(status="PENDENTE").count()
        ),
        "current_value_delta": contract.current_value - contract.original_value,
        "current_value": contract.current_value,
        "current_validity_end": contract.current_validity_end,
    }
