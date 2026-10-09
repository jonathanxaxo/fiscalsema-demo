from django import forms

from contracts.models import (
    BudgetCommitment,
    ContractItem,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderExecution,
)

from .models import Document, RelatedEntityType


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = (
            "title", "document_type", "origin", "related_entity_type",
            "item", "commitment", "work_order", "execution", "invoice",
            "payment", "previous_version", "file",
        )
        widgets = {"file": forms.ClearableFileInput(attrs={"accept": ".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.odt"})}

    def __init__(self, *args, contract, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract = contract
        self.instance.contract = contract
        self.fields["item"].queryset = ContractItem.objects.filter(contract=contract)
        self.fields["commitment"].queryset = BudgetCommitment.objects.filter(contract=contract)
        self.fields["work_order"].queryset = WorkOrder.objects.filter(contract=contract)
        self.fields["execution"].queryset = WorkOrderExecution.objects.filter(work_order__contract=contract)
        self.fields["invoice"].queryset = Invoice.objects.filter(contract=contract)
        self.fields["payment"].queryset = Payment.objects.filter(invoice__contract=contract)
        self.fields["previous_version"].queryset = Document.objects.filter(contract=contract)
        self.fields["previous_version"].required = False
        for field_name in ("item", "commitment", "work_order", "execution", "invoice", "payment"):
            self.fields[field_name].required = False
        self.fields["origin"].help_text = "Ex.: SIGADOC, SIAG, FORNECEDOR-DEMO ou Upload manual."
        self.fields["previous_version"].help_text = "Selecione somente quando este arquivo substituir uma versão anterior."

    def clean(self):
        cleaned = super().clean()
        mapping = {
            RelatedEntityType.ITEM: "item",
            RelatedEntityType.COMMITMENT: "commitment",
            RelatedEntityType.WORK_ORDER: "work_order",
            RelatedEntityType.EXECUTION: "execution",
            RelatedEntityType.INVOICE: "invoice",
            RelatedEntityType.PAYMENT: "payment",
        }
        selected = [name for name in mapping.values() if cleaned.get(name)]
        related_type = cleaned.get("related_entity_type")
        expected = mapping.get(related_type)
        if related_type == RelatedEntityType.CONTRACT and selected:
            self.add_error("related_entity_type", "Para o contrato, deixe as demais entidades vazias.")
        elif expected and not cleaned.get(expected):
            self.add_error(expected, "Selecione a entidade relacionada.")
        if len(selected) > 1 or (selected and selected[0] != expected):
            self.add_error("related_entity_type", "Informe somente a entidade correspondente.")
        return cleaned
