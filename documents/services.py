from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from contracts.services import contracts_visible_to, contracts_writable_by

from .models import Document, DocumentEvent
from .validators import inspect_upload


def documents_visible_to(actor):
    return Document.objects.select_related(
        "contract", "uploaded_by", "item", "commitment", "work_order",
        "execution", "invoice", "payment", "previous_version",
    ).filter(contract__in=contracts_visible_to(actor))


@transaction.atomic
def create_document(*, contract_id, actor, file, **data):
    if not actor.is_authenticated or not actor.has_perm("documents.add_document"):
        raise PermissionDenied("Permissão para anexar documentos necessária.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    metadata = inspect_upload(file)
    previous = data.get("previous_version")
    if previous:
        previous = Document.objects.select_for_update().get(
            pk=previous.pk, contract=contract
        )
        if hasattr(previous, "next_version"):
            raise ValidationError("A versão selecionada já possui uma sucessora.")
        comparable_fields = (
            "title", "document_type", "origin", "related_entity_type", "item",
            "commitment", "work_order", "execution", "invoice", "payment",
        )
        if any(data.get(field) != getattr(previous, field) for field in comparable_fields):
            raise ValidationError("Nova versão deve manter nome, tipo, origem e entidade da versão anterior.")
        version = previous.version + 1
    else:
        version = 1
    document = Document(
        contract=contract, file=file, uploaded_by=actor, version=version,
        **metadata, **data,
    )
    document.save()
    DocumentEvent.objects.create(
        event_type=DocumentEvent.EventType.UPLOADED,
        document=document,
        contract=contract,
        actor=actor,
        details={
            "atual": {
                "documento_id": document.pk,
                "nome": document.title,
                "tipo": document.document_type,
                "versao": document.version,
                "sha256": document.sha256,
            }
        },
    )
    return document
