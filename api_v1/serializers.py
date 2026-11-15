from dataclasses import asdict, is_dataclass
from decimal import Decimal

from contracts.periods import annual_context, calendar_year_periods, contract_year_periods


def period_data(period):
    if period is None:
        return None
    return {
        "kind": period.kind,
        "ordinal": period.ordinal,
        "label": period.label,
        "start_date": period.start_date.isoformat(),
        "end_date": period.end_date.isoformat(),
    }


def primitive(value):
    if is_dataclass(value):
        return primitive(asdict(value))
    if isinstance(value, dict):
        return {key: primitive(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [primitive(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def contract_data(contract):
    return {
        "id": contract.pk, "number": contract.number,
        "process_number": contract.process_number, "object": contract.object,
        "organization": {"id": contract.contracting_organization_id,
                         "name": contract.contracting_organization.name},
        "supplier": {"name": contract.supplier_name, "tax_id": contract.supplier_tax_id},
        "signature_date": contract.signature_date.isoformat(),
        "validity_start": contract.validity_start.isoformat(),
        "validity_end": contract.validity_end.isoformat(),
        "original_value": str(contract.original_value),
        "current_value": str(contract.current_value), "status": contract.status,
        "responsible_fiscal": {"id": contract.responsible_fiscal_id,
                               "name": contract.responsible_fiscal.full_name},
        "annual_periods": {
            "official_closing_rule": "CALENDAR_YEAR",
            "calendar_years": [period_data(item) for item in calendar_year_periods(contract)],
            "contract_years": [period_data(item) for item in contract_year_periods(contract)],
        },
    }


def commitment_data(item):
    return {
        "id": item.pk, "number": item.number, "ped": item.ped,
        "date": item.commitment_date.isoformat(), "initial_value": str(item.initial_value),
        "fiscal_year": item.fiscal_year,
        "current_value": str(item.current_value), "source": item.source, "active": item.is_active,
        "accepts_new_allocations": item.accepts_new_allocations,
        "closed_for_new_allocations_at": (
            item.closed_for_new_allocations_at.isoformat()
            if item.closed_for_new_allocations_at else None
        ),
        "movements": [
            {
                "type": movement.movement_type,
                "date": movement.movement_date.isoformat(),
                "amount": str(movement.amount),
                "document_reference": movement.document_reference,
            }
            for movement in item.movements.all()
        ],
    }


def work_order_data(item):
    periods = annual_context(item.contract, item.opening_date)
    return {
        "id": item.pk, "number": item.number, "item_id": item.item_id,
        "description": item.description, "quantity": str(item.quantity) if item.quantity is not None else None,
        "hours": str(item.hours) if item.hours is not None else None,
        "unit_value": str(item.unit_value), "total_value": str(item.total_value),
        "responsible": item.responsible, "opening_date": item.opening_date.isoformat(),
        "deadline": item.deadline.isoformat() if item.deadline else None,
        "status": item.status, "process_number": item.process_number,
        "annual_periods": {key: period_data(value) for key, value in periods.items()},
        # Sprint 40: prazos (Sprint 36) e memória de cálculo (Sprint 38).
        "factory_deadline": item.factory_deadline.isoformat() if item.factory_deadline else None,
        "spent_hours_informed": str(item.spent_hours) if item.spent_hours is not None else None,
        "deadline_situation": _deadline_situation_data(item),
        "service_lines": [service_line_data(line) for line in item.service_lines.all()],
    }


def _deadline_situation_data(work_order):
    situation = work_order.deadline_situation
    return {
        "code": situation.code, "label": situation.label,
        "contract_countdown": situation.contract_countdown.text if situation.contract_countdown else None,
        "factory_countdown": situation.factory_countdown.text if situation.factory_countdown else None,
    }


def service_line_data(line):
    return {
        "id": line.pk, "service_code": line.service_code, "service_name": line.service_name,
        "measure_label": line.measure_label, "complexity": line.complexity,
        "quantity": str(line.quantity), "weight": str(line.weight), "units": str(line.units),
        "status": line.delivery_status,
        "homologation_reference": line.homologation_reference or None,
    }


def invoice_data(item):
    return {
        "id": item.pk, "number": item.number, "series": item.series,
        "work_order_id": item.work_order_id, "item_id": item.item_id,
        "allocation_id": item.allocation_id, "supplier_name": item.supplier_name,
        "supplier_tax_id": item.supplier_tax_id, "issue_date": item.issue_date.isoformat(),
        "competence": item.competence, "gross_value": str(item.gross_value),
        "deduction_value": str(item.deduction_value), "accepted_value": str(item.accepted_value),
        "process_number": item.process_number, "status": item.status,
        # Sprint 40: NF pelo valor dimensionado e devolução (Sprint 39).
        "is_returned": item.is_returned,
        "returned_at": item.returned_at.isoformat() if item.returned_at else None,
        "return_reason": item.return_reason or None,
        "replaces_invoice_id": item.replaces_id,
        "billed_service_line_ids": sorted(line.pk for line in item.service_lines.all()),
        "dimensioned_value": None if item.dimensioned_value is None else str(item.dimensioned_value),
        "counts_in_calculations": not item.is_returned,
    }


def item_data(item):
    return {
        "id": item.pk, "number": item.number, "external_code": item.external_code,
        "description": item.description,
        "category": item.category, "unit": item.unit,
        "custom_unit_name": item.custom_unit_name,
        "contracted_quantity": str(item.contracted_quantity),
        "annual_reference_quantity": (
            str(item.annual_reference_quantity)
            if item.annual_reference_quantity is not None else None
        ),
        "annual_reference_unit": item.annual_reference_unit,
        "annual_operational_limit": (
            str(item.annual_operational_limit)
            if item.annual_operational_limit is not None else None
        ),
        "unit_value": str(item.unit_value), "total_value": str(item.total_value),
        "calculation_rule": item.calculation_rule,
        "source_reference": item.source_reference,
        "active": item.is_active,
    }


def allocation_data(item):
    return {
        "id": item.pk, "work_order_id": item.work_order_id,
        "commitment_id": item.commitment_id, "amount": str(item.amount),
        "date": item.allocation_date.isoformat(), "status": item.status,
    }


def execution_data(item):
    return {
        "id": item.pk, "work_order_id": item.work_order_id,
        "executed_quantity": str(item.executed_quantity),
        "executed_value": str(item.executed_value),
        "date": item.execution_date.isoformat(), "competence": item.competence,
        "evidence_reference": item.evidence_reference,
    }


def payment_data(item):
    return {
        "id": item.pk, "invoice_id": item.invoice_id, "amount": str(item.amount),
        "date": item.payment_date.isoformat(), "competence": item.competence,
        "status": item.status, "process_number": item.process_number,
        "has_attestation": bool(item.attestation_reference),
        "has_raer": bool(item.raer_reference),
        "has_homologation": bool(item.homologation_reference),
        "has_payment_evidence": bool(item.evidence_reference),
    }


def document_data(item):
    return {
        "id": item.pk, "title": item.title, "document_type": item.document_type,
        "origin": item.origin, "related_entity_type": item.related_entity_type,
        "version": item.version, "original_name": item.original_name,
        "mime_type": item.mime_type, "file_size": item.file_size,
        "sha256": item.sha256, "uploaded_at": item.uploaded_at.isoformat(),
        "content_url": f"/api/v1/documents/{item.pk}/content/",
    }
