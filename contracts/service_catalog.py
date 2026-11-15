"""Catálogo de serviços do contrato e memória de cálculo da OS (Sprint 38).

Referência: FiscalSema Light (ADR 0021/0022), somente lido; adaptado ao Demo.

Regras:

- o catálogo pertence ao contrato e registra, por serviço, o peso em
  UST/HST/USN por unidade de medida, para cada complexidade;
- a OS recebe linhas "serviço × complexidade × quantidade"; o peso, o código e
  o nome são copiados do catálogo e ficam congelados na linha;
- quando a OS tem linhas, a quantidade da OS passa a ser a soma das UST/HST/USN
  das linhas, e o valor continua sendo quantidade × valor unitário de
  referência (mesma camada de cálculo de sempre);
- toda alteração passa pelas mesmas validações de saldo da edição de OS e fica
  registrada na auditoria do contrato ou da OS.
"""

from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .calculations import calculate_service_units
from .models import (
    ContractEvent,
    ServiceCatalogEntry,
    ServiceComplexity,
    ServiceLineStatus,
    WorkOrderEvent,
    WorkOrderServiceLine,
    WorkOrderStatus,
)
from .services import (
    _validate_work_order_allocations,
    _validate_work_order_capacity,
    _validate_work_order_executions,
    _validate_work_order_invoices,
    contracts_visible_to,
    contracts_writable_by,
    work_order_snapshot,
    work_orders_writable_by,
)

CATALOG_FIELDS = (
    "code",
    "name",
    "measure_label",
    "weight_low",
    "weight_medium",
    "weight_high",
    "source_reference",
    "is_active",
)


def _decimal_text(value):
    return None if value is None else str(value)


def catalog_entry_snapshot(entry):
    return {
        "servico_id": entry.pk,
        "codigo": entry.code,
        "servico": entry.name,
        "unidade_medida": entry.measure_label,
        "peso_baixa": _decimal_text(entry.weight_low),
        "peso_media": _decimal_text(entry.weight_medium),
        "peso_alta": _decimal_text(entry.weight_high),
        "fonte": entry.source_reference,
        "ativo": entry.is_active,
    }


def service_line_snapshot(line):
    return {
        "linha_id": line.pk,
        "servico_id": line.catalog_entry_id,
        "codigo": line.service_code,
        "servico": line.service_name,
        "unidade_medida": line.measure_label,
        "complexidade": line.complexity,
        "quantidade": str(line.quantity),
        "peso": str(line.weight),
        "unidades": str(line.units),
        "situacao": line.delivery_status,
        "entregue_em": line.delivered_at.isoformat() if line.delivered_at else None,
        "aceito_em": line.accepted_at.isoformat() if line.accepted_at else None,
        "homologado_em": line.homologated_at.isoformat() if line.homologated_at else None,
        "termo_homologacao": line.homologation_reference,
        "recusas": line.rejection_count,
    }


def catalog_visible_to(actor, contract_id):
    contract = contracts_visible_to(actor).filter(pk=contract_id).first()
    if contract is None:
        return ServiceCatalogEntry.objects.none()
    return contract.service_catalog.all()


def _writable_contract(actor, contract_id):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_contract"):
        raise PermissionDenied("Permissão para alterar o catálogo do contrato necessária.")
    return contracts_writable_by(actor).select_for_update().get(pk=contract_id)


@transaction.atomic
def create_service_catalog_entry(*, contract_id, actor, **data):
    contract = _writable_contract(actor, contract_id)
    entry = ServiceCatalogEntry(contract=contract, created_by=actor, **data)
    entry.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CATALOG_SERVICE_CREATED,
        contract=contract,
        actor=actor,
        details={"atual": catalog_entry_snapshot(entry)},
    )
    return entry


@transaction.atomic
def update_service_catalog_entry(*, entry_id, actor, **data):
    entry = ServiceCatalogEntry.objects.select_for_update().get(pk=entry_id)
    contract = _writable_contract(actor, entry.contract_id)
    previous = catalog_entry_snapshot(entry)
    for field in CATALOG_FIELDS:
        if field in data:
            setattr(entry, field, data[field])
    entry.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CATALOG_SERVICE_UPDATED,
        contract=contract,
        actor=actor,
        details={"anterior": previous, "atual": catalog_entry_snapshot(entry)},
    )
    return entry


def _lock_writable_work_order(actor, work_order_id):
    work_order = work_orders_writable_by(actor).select_for_update(of=("self",)).get(
        pk=work_order_id
    )
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("OS cancelada é somente leitura.")
    if work_order.hours is not None:
        raise ValidationError(
            "O catálogo de serviços vale para OS medidas em quantidade "
            "(UST, HST, USN ou outra unidade). Esta OS é medida em horas."
        )
    return work_order


def _weight_for(entry, complexity):
    if complexity not in ServiceComplexity.values:
        raise ValidationError({"complexity": "Complexidade inválida."})
    weight = entry.weight_for(complexity)
    if weight is None:
        raise ValidationError(
            {"complexity": "O serviço não tem peso cadastrado para essa complexidade."}
        )
    return weight


def _recalculate_work_order(work_order, *, actor, event_type, line_details):
    previous = work_order_snapshot(work_order)
    lines = tuple(work_order.service_lines.all())
    if lines:
        work_order.quantity = sum(
            (calculate_service_units(line.quantity, line.weight) for line in lines),
            Decimal("0"),
        )
    work_order.full_clean()
    _validate_work_order_capacity(work_order, exclude_id=work_order.pk)
    _validate_work_order_allocations(work_order)
    _validate_work_order_executions(work_order)
    _validate_work_order_invoices(work_order)
    work_order.save()
    WorkOrderEvent.objects.create(
        event_type=event_type,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": work_order_snapshot(work_order),
            **line_details,
        },
    )
    return work_order


@transaction.atomic
def add_work_order_service_line(*, work_order_id, actor, catalog_entry, complexity, quantity):
    work_order = _lock_writable_work_order(actor, work_order_id)
    entry = ServiceCatalogEntry.objects.filter(
        pk=getattr(catalog_entry, "pk", catalog_entry),
        contract_id=work_order.contract_id,
    ).first()
    if entry is None:
        raise ValidationError({"catalog_entry": "Serviço não pertence ao catálogo do contrato."})
    if not entry.is_active:
        raise ValidationError({"catalog_entry": "Serviço inativo não pode ser incluído em OS."})
    line = WorkOrderServiceLine(
        work_order=work_order,
        catalog_entry=entry,
        service_code=entry.code,
        service_name=entry.name,
        measure_label=entry.measure_label,
        complexity=complexity,
        quantity=quantity,
        weight=_weight_for(entry, complexity),
        created_by=actor,
    )
    line.save()
    _recalculate_work_order(
        work_order,
        actor=actor,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_ADDED,
        line_details={"linha": service_line_snapshot(line)},
    )
    return line


@transaction.atomic
def update_work_order_service_line(*, line_id, actor, complexity, quantity):
    line = WorkOrderServiceLine.objects.select_for_update().get(pk=line_id)
    work_order = _lock_writable_work_order(actor, line.work_order_id)
    _require_in_progress(line)
    previous = service_line_snapshot(line)
    if complexity != line.complexity:
        line.weight = _weight_for(line.catalog_entry, complexity)
        line.complexity = complexity
    line.quantity = quantity
    line.save()
    _recalculate_work_order(
        work_order,
        actor=actor,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_UPDATED,
        line_details={"linha_anterior": previous, "linha": service_line_snapshot(line)},
    )
    return line


@transaction.atomic
def remove_work_order_service_line(*, line_id, actor):
    line = WorkOrderServiceLine.objects.select_for_update().get(pk=line_id)
    work_order = _lock_writable_work_order(actor, line.work_order_id)
    _require_in_progress(line)
    snapshot = service_line_snapshot(line)
    line.delete()
    _recalculate_work_order(
        work_order,
        actor=actor,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_REMOVED,
        line_details={"linha_removida": snapshot},
    )


def _require_in_progress(line):
    if line.delivery_status != ServiceLineStatus.IN_PROGRESS:
        raise ValidationError(
            "Só é possível alterar ou remover serviço em andamento. "
            "Serviço entregue, aceito ou homologado preserva a medição registrada."
        )


def _validate_event_date(value, *, field, work_order, not_before=None, label_before=""):
    if value is None:
        raise ValidationError({field: "Informe a data."})
    if value > timezone.localdate():
        raise ValidationError({field: "A data não pode ser futura."})
    if value < work_order.opening_date:
        raise ValidationError({field: "A data não pode ser anterior à abertura da OS."})
    if not_before and value < not_before:
        raise ValidationError({field: f"A data não pode ser anterior {label_before}."})


def _line_transition(*, line_id, actor, allowed_from, apply, event_type, extra=None):
    line = WorkOrderServiceLine.objects.select_for_update().get(pk=line_id)
    work_order = _lock_any_status_work_order(actor, line.work_order_id)
    if line.delivery_status not in allowed_from:
        raise ValidationError(
            f"Ação não permitida para serviço na situação "
            f"\"{line.get_delivery_status_display()}\"."
        )
    previous = service_line_snapshot(line)
    apply(line, work_order)
    line.save()
    WorkOrderEvent.objects.create(
        event_type=event_type,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"linha_anterior": previous, "linha": service_line_snapshot(line), **(extra or {})},
    )
    return line


def _lock_any_status_work_order(actor, work_order_id):
    work_order = work_orders_writable_by(actor).select_for_update(of=("self",)).get(
        pk=work_order_id
    )
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("OS cancelada é somente leitura.")
    return work_order


@transaction.atomic
def register_service_line_delivery(*, line_id, actor, delivered_at):
    def apply(line, work_order):
        _validate_event_date(delivered_at, field="delivered_at", work_order=work_order)
        line.delivery_status = ServiceLineStatus.DELIVERED
        line.delivered_at = delivered_at

    return _line_transition(
        line_id=line_id,
        actor=actor,
        allowed_from={ServiceLineStatus.IN_PROGRESS},
        apply=apply,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_DELIVERED,
    )


@transaction.atomic
def accept_service_line(*, line_id, actor, accepted_at):
    def apply(line, work_order):
        _validate_event_date(
            accepted_at,
            field="accepted_at",
            work_order=work_order,
            not_before=line.delivered_at,
            label_before="à entrega",
        )
        line.delivery_status = ServiceLineStatus.ACCEPTED
        line.accepted_at = accepted_at

    return _line_transition(
        line_id=line_id,
        actor=actor,
        allowed_from={ServiceLineStatus.DELIVERED},
        apply=apply,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_ACCEPTED,
    )


@transaction.atomic
def reject_service_line(*, line_id, actor, rejected_at, reason):
    reason = " ".join((reason or "").split())
    if not reason:
        raise ValidationError({"reason": "Informe o motivo da recusa."})

    def apply(line, work_order):
        _validate_event_date(
            rejected_at,
            field="rejected_at",
            work_order=work_order,
            not_before=line.delivered_at,
            label_before="à entrega",
        )
        line.delivery_status = ServiceLineStatus.IN_PROGRESS
        line.delivered_at = None
        line.accepted_at = None
        line.rejection_count += 1
        line.last_rejection_reason = reason

    return _line_transition(
        line_id=line_id,
        actor=actor,
        allowed_from={ServiceLineStatus.DELIVERED, ServiceLineStatus.ACCEPTED},
        apply=apply,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_REJECTED,
        extra={"recusa": {"data": rejected_at.isoformat() if rejected_at else None, "motivo": reason}},
    )


@transaction.atomic
def homologate_service_line(*, line_id, actor, homologated_at, reference):
    reference = " ".join((reference or "").split())
    if not reference:
        raise ValidationError({"reference": "Informe o número do Termo de Homologação."})

    def apply(line, work_order):
        _validate_event_date(
            homologated_at,
            field="homologated_at",
            work_order=work_order,
            not_before=line.accepted_at,
            label_before="ao aceite",
        )
        line.delivery_status = ServiceLineStatus.HOMOLOGATED
        line.homologated_at = homologated_at
        line.homologation_reference = reference

    return _line_transition(
        line_id=line_id,
        actor=actor,
        allowed_from={ServiceLineStatus.ACCEPTED},
        apply=apply,
        event_type=WorkOrderEvent.EventType.SERVICE_LINE_HOMOLOGATED,
    )


@transaction.atomic
def homologate_accepted_service_lines(*, work_order_id, actor, homologated_at, reference):
    lines = tuple(
        WorkOrderServiceLine.objects.filter(
            work_order_id=work_order_id, delivery_status=ServiceLineStatus.ACCEPTED
        ).values_list("pk", flat=True)
    )
    if not lines:
        raise ValidationError("Não há serviços aceitos aguardando homologação nesta OS.")
    return [
        homologate_service_line(
            line_id=line_id, actor=actor, homologated_at=homologated_at, reference=reference
        )
        for line_id in lines
    ]


def work_order_service_summary(work_order):
    """Linhas e totais da memória de cálculo de uma OS (somente leitura)."""
    lines = tuple(work_order.service_lines.order_by("pk"))
    total_units = sum((line.units for line in lines), Decimal("0"))
    counts = {status: 0 for status in ServiceLineStatus.values}
    for line in lines:
        counts[line.delivery_status] += 1
    return {
        "lines": lines,
        "status_counts": counts,
        "accepted_count": counts[ServiceLineStatus.ACCEPTED],
        "total_units": total_units,
        "total_value": work_order.total_value if lines else None,
        "has_lines": bool(lines),
        "matches_work_order": (not lines) or total_units == work_order.quantity,
    }
