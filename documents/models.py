import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class DocumentType(models.TextChoices):
    CONTRACT = "CONTRATO", "Contrato"
    TERMS_OF_REFERENCE = "TERMO_REFERENCIA", "Termo de referência"
    NOTICE = "EDITAL", "Edital"
    AMENDMENT = "ADITIVO", "Aditivo"
    COMMITMENT = "EMPENHO", "Empenho"
    WORK_ORDER = "OS", "Ordem de Serviço"
    VISION = "DOCUMENTO_VISAO", "Documento de Visão"
    REPORT = "RELATORIO", "Relatório"
    MEASUREMENT = "MEDICAO", "Medição"
    CALCULATION = "MEMORIA_CALCULO", "Memória de cálculo"
    ACCEPTANCE = "TERMO_ACEITE", "Termo de aceite"
    INVOICE = "NOTA_FISCAL", "Nota Fiscal"
    PAYMENT_PROOF = "COMPROVANTE_PAGAMENTO", "Comprovante de pagamento"
    OTHER = "OUTRO", "Outro"


class RelatedEntityType(models.TextChoices):
    CONTRACT = "CONTRATO", "Contrato"
    ITEM = "ITEM", "Item"
    COMMITMENT = "EMPENHO", "Empenho"
    WORK_ORDER = "OS", "Ordem de Serviço"
    EXECUTION = "EXECUCAO", "Execução"
    INVOICE = "NOTA_FISCAL", "Nota Fiscal"
    PAYMENT = "PAGAMENTO", "Pagamento"


def document_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()
    now = timezone.now()
    return f"contratos/{instance.contract_id}/{now:%Y/%m}/{uuid.uuid4().hex}{extension}"


class Document(models.Model):
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT, related_name="documents",
        verbose_name="contrato",
    )
    title = models.CharField("nome", max_length=255)
    document_type = models.CharField(
        "tipo", max_length=30, choices=DocumentType.choices, db_index=True,
    )
    origin = models.CharField("origem", max_length=200, default="Upload manual")
    related_entity_type = models.CharField(
        "entidade relacionada", max_length=20,
        choices=RelatedEntityType.choices, default=RelatedEntityType.CONTRACT,
    )
    item = models.ForeignKey(
        "contracts.ContractItem", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="item",
    )
    commitment = models.ForeignKey(
        "contracts.BudgetCommitment", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="empenho",
    )
    work_order = models.ForeignKey(
        "contracts.WorkOrder", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="Ordem de Serviço",
    )
    execution = models.ForeignKey(
        "contracts.WorkOrderExecution", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="execução",
    )
    invoice = models.ForeignKey(
        "contracts.Invoice", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="Nota Fiscal",
    )
    payment = models.ForeignKey(
        "contracts.Payment", on_delete=models.PROTECT, null=True, blank=True,
        related_name="documents", verbose_name="pagamento",
    )
    file = models.FileField("arquivo", upload_to=document_upload_path, max_length=500)
    original_name = models.CharField("nome original", max_length=255)
    mime_type = models.CharField("tipo MIME", max_length=100)
    file_size = models.PositiveIntegerField("tamanho em bytes")
    sha256 = models.CharField("SHA-256", max_length=64, db_index=True, editable=False)
    version = models.PositiveIntegerField("versão", default=1, editable=False)
    previous_version = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True,
        related_name="next_version", verbose_name="versão anterior",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="uploaded_documents", verbose_name="responsável",
    )
    uploaded_at = models.DateTimeField("enviado em", auto_now_add=True)

    class Meta:
        ordering = ("-uploaded_at", "-pk")
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(version__gte=1), name="documents_version_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(file_size__gt=0), name="documents_file_size_positive"
            ),
        ]

    def clean(self):
        super().clean()
        self.title = " ".join((self.title or "").split())
        self.origin = " ".join((self.origin or "").split())
        errors = {}
        if not self.title:
            errors["title"] = "Informe o nome do documento."
        if not self.origin:
            errors["origin"] = "Informe a origem do documento."
        relations = {
            RelatedEntityType.ITEM: self.item,
            RelatedEntityType.COMMITMENT: self.commitment,
            RelatedEntityType.WORK_ORDER: self.work_order,
            RelatedEntityType.EXECUTION: self.execution,
            RelatedEntityType.INVOICE: self.invoice,
            RelatedEntityType.PAYMENT: self.payment,
        }
        populated = [key for key, value in relations.items() if value is not None]
        if self.related_entity_type == RelatedEntityType.CONTRACT:
            if populated:
                errors["related_entity_type"] = "Documento do contrato não deve apontar outra entidade."
        elif relations.get(self.related_entity_type) is None:
            errors[self._field_for_entity()] = "Selecione a entidade relacionada."
        if len(populated) > 1 or (populated and populated[0] != self.related_entity_type):
            errors["related_entity_type"] = "Informe somente a entidade correspondente ao tipo selecionado."
        for value in relations.values():
            related_contract_id = None
            if value is not None:
                related_contract_id = getattr(value, "contract_id", None)
                if isinstance(value, self._meta.apps.get_model("contracts", "WorkOrderExecution")):
                    related_contract_id = value.work_order.contract_id
                if isinstance(value, self._meta.apps.get_model("contracts", "Payment")):
                    related_contract_id = value.invoice.contract_id
            if value is not None and related_contract_id != self.contract_id:
                errors["related_entity_type"] = "A entidade deve pertencer ao mesmo contrato."
        if self.previous_version_id:
            previous = self.previous_version
            if previous.contract_id != self.contract_id:
                errors["previous_version"] = "A versão anterior deve pertencer ao mesmo contrato."
            if previous.pk == self.pk:
                errors["previous_version"] = "Um documento não pode versionar a si próprio."
        if errors:
            raise ValidationError(errors)

    def _field_for_entity(self):
        return {
            RelatedEntityType.ITEM: "item",
            RelatedEntityType.COMMITMENT: "commitment",
            RelatedEntityType.WORK_ORDER: "work_order",
            RelatedEntityType.EXECUTION: "execution",
            RelatedEntityType.INVOICE: "invoice",
            RelatedEntityType.PAYMENT: "payment",
        }.get(self.related_entity_type, "related_entity_type")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Documentos são imutáveis; envie uma nova versão.")
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Documentos não podem ser excluídos pelo fluxo normal.")

    def __str__(self):
        return f"{self.title} — v{self.version}"


class DocumentEvent(models.Model):
    class EventType(models.TextChoices):
        UPLOADED = "DOCUMENTO_ENVIADO", "Documento enviado"
        DOWNLOADED = "DOCUMENTO_BAIXADO", "Documento baixado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    document = models.ForeignKey(
        Document, on_delete=models.PROTECT, related_name="events", verbose_name="documento"
    )
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT,
        related_name="document_events", verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="document_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de documento"
        verbose_name_plural = "eventos de documentos"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.document}"
