from django import forms

from .models import (
    BudgetCommitment,
    CommitmentMovement,
    Contract,
    ContractItem,
    ContractStatus,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderAllocation,
    WorkOrderAllocationStatus,
    WorkOrderExecution,
    WorkOrderStatus,
)
from .periods import calendar_year_periods, contract_year_periods


def _html_date_input():
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})


def _localize_decimal_fields(form, *field_names):
    """Use locale-aware text inputs so comma decimals are not cleared by HTML."""
    for name in field_names:
        field = form.fields[name]
        field.localize = True
        field.widget = forms.TextInput(
            attrs={**field.widget.attrs, "inputmode": "decimal"}
        )
        field.widget.is_localized = True


class AccountabilityFilterForm(forms.Form):
    annual_period = forms.ChoiceField(
        label="Período anual",
        required=False,
        choices=(),
    )
    start_date = forms.DateField(
        label="Data inicial", required=False,
        widget=_html_date_input(),
    )
    end_date = forms.DateField(
        label="Data final", required=False,
        widget=_html_date_input(),
    )
    competence = forms.RegexField(
        label="Competência", required=False, regex=r"^(0[1-9]|1[0-2])/\d{4}$",
        error_messages={"invalid": "Informe a competência no formato MM/AAAA."},
    )
    commitment = forms.ModelChoiceField(
        label="Empenho", required=False, queryset=BudgetCommitment.objects.none()
    )
    work_order = forms.ModelChoiceField(
        label="Ordem de Serviço", required=False, queryset=WorkOrder.objects.none()
    )
    invoice = forms.ModelChoiceField(
        label="Nota Fiscal", required=False, queryset=Invoice.objects.none()
    )

    def __init__(self, *args, contract, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract = contract
        self.fields["annual_period"].choices = [
            ("", "Todos os períodos"),
            *(
                (
                    f"civil:{period.ordinal}",
                    f"{period.label} — {period.start_date:%d/%m/%Y} a {period.end_date:%d/%m/%Y}",
                )
                for period in calendar_year_periods(contract)
            ),
            *(
                (
                    f"contratual:{period.ordinal}",
                    f"{period.label} — {period.start_date:%d/%m/%Y} a {period.end_date:%d/%m/%Y}",
                )
                for period in contract_year_periods(contract)
            ),
        ]
        self.fields["commitment"].queryset = contract.commitments.all()
        self.fields["work_order"].queryset = contract.work_orders.all()
        self.fields["invoice"].queryset = contract.invoices.all()

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        annual_period = cleaned.get("annual_period")
        if annual_period and (start_date or end_date):
            raise forms.ValidationError(
                "Escolha um período anual ou informe datas manuais, não ambos."
            )
        if annual_period:
            kind, ordinal_text = annual_period.split(":", 1)
            periods = (
                calendar_year_periods(self.contract)
                if kind == "civil"
                else contract_year_periods(self.contract)
            )
            period = next(
                (item for item in periods if item.ordinal == int(ordinal_text)),
                None,
            )
            if period is None:
                raise forms.ValidationError("Período anual inválido para o contrato.")
            cleaned["start_date"] = period.start_date
            cleaned["end_date"] = period.end_date
            start_date = period.start_date
            end_date = period.end_date
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("A data inicial não pode ser posterior à final.")
        return cleaned


class ReportFilterForm(AccountabilityFilterForm):
    class Section:
        ALL = "all"
        FINANCIAL = "financial"
        OPERATIONAL = "operational"
        BILLING = "billing"

    section = forms.ChoiceField(
        label="Conteúdo",
        required=False,
        choices=(
            (Section.ALL, "Relatório completo"),
            (Section.FINANCIAL, "Resumo financeiro"),
            (Section.OPERATIONAL, "Operação: empenhos, OS e execução"),
            (Section.BILLING, "Faturamento: NF e pagamentos"),
        ),
        initial=Section.ALL,
    )
    status = forms.ChoiceField(label="Status", required=False, choices=())

    def __init__(self, *args, contract, **kwargs):
        super().__init__(*args, contract=contract, **kwargs)
        status_choices = [("", "Todos os status")]
        status_choices.extend(
            (f"OS:{value}", f"OS — {label}")
            for value, label in WorkOrderStatus.choices
            if contract.work_orders.filter(status=value).exists()
        )
        status_choices.extend(
            (f"NF:{value}", f"Nota Fiscal — {value}")
            for value in contract.invoices.order_by("status")
            .values_list("status", flat=True)
            .distinct()
        )
        status_choices.extend(
            (f"PAGAMENTO:{value}", f"Pagamento — {value}")
            for value in Payment.objects.filter(invoice__contract=contract)
            .order_by("status")
            .values_list("status", flat=True)
            .distinct()
        )
        self.fields["status"].choices = status_choices


class ContractShareForm(forms.Form):
    email = forms.EmailField(
        label="E-mail da pessoa",
        max_length=254,
        help_text="O acesso concedido será exclusivamente Somente leitura.",
    )
    confirm_regrant = forms.BooleanField(
        required=False,
        label="Confirmo a reativação de um acesso anteriormente revogado",
        help_text=(
            "Marque somente quando o sistema informar que este e-mail possui "
            "um acesso revogado que precisa ser concedido novamente."
        ),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()


class FiscalSubstitutionForm(forms.Form):
    email = forms.EmailField(
        label="E-mail do Fiscal substituto",
        max_length=254,
        help_text=(
            "Use o e-mail individual do Fiscal. Se ainda não houver conta, "
            "o vínculo aguardará cadastro e aprovação administrativa."
        ),
    )
    starts_on = forms.DateField(
        label="Início da substituição",
        widget=_html_date_input(),
    )
    ends_on = forms.DateField(
        label="Fim da substituição",
        widget=_html_date_input(),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()

    def clean(self):
        cleaned_data = super().clean()
        starts_on = cleaned_data.get("starts_on")
        ends_on = cleaned_data.get("ends_on")
        if starts_on and ends_on and ends_on < starts_on:
            self.add_error(
                "ends_on", "O fim da substituição não pode anteceder o início."
            )
        return cleaned_data


def tax_id_field(label="CNPJ/CPF do fornecedor"):
    """CPF/CNPJ aceito com ou sem pontuação; a tela aplica a máscara ao digitar (Sprint 35)."""
    return forms.CharField(
        label=label,
        max_length=18,
        help_text="Digite os 11 dígitos do CPF ou os 14 do CNPJ; a pontuação é aplicada automaticamente.",
        widget=forms.TextInput(attrs={
            "inputmode": "numeric", "autocomplete": "off", "data-tax-id": "",
            "placeholder": "000.000.000-00 ou 00.000.000/0000-00",
        }),
    )


def clean_tax_id(value):
    digits = "".join(character for character in (value or "") if character.isdigit())
    if len(digits) not in (11, 14):
        raise forms.ValidationError("Informe CPF com 11 dígitos ou CNPJ com 14 dígitos.")
    return digits


def format_tax_id(value):
    digits = "".join(character for character in (value or "") if character.isdigit())
    if len(digits) == 14:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"
    if len(digits) == 11:
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
    return value or ""


class ContractForm(forms.ModelForm):
    supplier_tax_id = tax_id_field()

    class Meta:
        model = Contract
        fields = (
            "number",
            "process_number",
            "object",
            "supplier_name",
            "supplier_tax_id",
            "signature_date",
            "validity_start",
            "validity_end",
            "original_value",
            "status",
            "notes",
        )
        widgets = {
            "signature_date": _html_date_input(),
            "validity_start": _html_date_input(),
            "validity_end": _html_date_input(),
            "object": forms.Textarea(attrs={"rows": 4}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "original_value": "O valor atual será igual ao original até a implementação de aditivos.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            choice
            for choice in ContractStatus.choices
            if choice[0] not in (ContractStatus.CLOSED, ContractStatus.CANCELED)
        ]
        _localize_decimal_fields(self, "original_value")
        if not self.is_bound and self.instance.pk:
            self.initial["supplier_tax_id"] = format_tax_id(self.instance.supplier_tax_id)

    def clean_supplier_tax_id(self):
        return clean_tax_id(self.cleaned_data["supplier_tax_id"])


class ContractCloseForm(forms.Form):
    reason = forms.CharField(
        label="Justificativa do encerramento",
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=(
            "Informe o fundamento administrativo do encerramento. "
            "O histórico e os dados do contrato serão preservados."
        ),
    )
    confirmed = forms.BooleanField(
        label=(
            "Confirmo que todas as Ordens de Serviço estão concluídas ou canceladas "
            "e que o contrato ficará somente para consulta"
        )
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe a justificativa do encerramento.")
        return reason


class ContractTransferForm(forms.Form):
    email = forms.EmailField(
        label="E-mail do novo Fiscal responsável",
        max_length=254,
        help_text="A conta deve ser de um Fiscal ativo da mesma organização.",
    )
    reason = forms.CharField(
        label="Justificativa da transferência",
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    confirmed = forms.BooleanField(
        label=(
            "Confirmo a transferência da responsabilidade e a revogação das "
            "substituições temporárias vigentes ou pendentes"
        )
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().casefold()

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe a justificativa da transferência.")
        return reason


class ContractArchiveForm(forms.Form):
    reason = forms.CharField(
        label="Justificativa do arquivamento",
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text=(
            "Use somente para contrato cadastrado incorretamente e ainda sem histórico "
            "operacional. Nenhum registro será apagado fisicamente."
        ),
    )
    confirmed = forms.BooleanField(
        label=(
            "Confirmo que este contrato foi cadastrado incorretamente e deve sair "
            "das telas operacionais"
        )
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe a justificativa do arquivamento.")
        return reason


class ContractRestoreForm(forms.Form):
    reason = forms.CharField(
        label="Justificativa da restauração",
        widget=forms.Textarea(attrs={"rows": 5}),
    )
    confirmed = forms.BooleanField(
        label="Confirmo a restauração deste contrato para as telas operacionais"
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe a justificativa da restauração.")
        return reason


class ContractItemForm(forms.ModelForm):
    class Meta:
        model = ContractItem
        fields = (
            "number",
            "external_code",
            "description",
            "category",
            "unit",
            "custom_unit_name",
            "contracted_quantity",
            "annual_reference_quantity",
            "annual_reference_unit",
            "annual_operational_limit",
            "unit_value",
            "calculation_rule",
            "source_reference",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "calculation_rule": forms.Textarea(attrs={"rows": 4}),
            "source_reference": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "custom_unit_name": "Obrigatório somente quando a unidade for Personalizada.",
            "contracted_quantity": "Aceita até quatro casas decimais.",
            "annual_reference_quantity": (
                "Referência da fonte oficial por ano contratual; não altera o valor total."
            ),
            "annual_reference_unit": "Ex.: pacote anual de 10 usuários, HST por ano.",
            "annual_operational_limit": (
                "Limite de quantidade das OS em cada aniversário da vigência. "
                "Deixe vazio quando a fonte ainda exigir definição."
            ),
            "unit_value": "Informe o valor monetário em reais.",
            "calculation_rule": (
                "Registre como a referência anual, o período e a unidade resultam "
                "na quantidade operacional total."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _localize_decimal_fields(
            self,
            "contracted_quantity",
            "annual_reference_quantity",
            "annual_operational_limit",
            "unit_value",
        )


class BudgetCommitmentForm(forms.ModelForm):
    class Meta:
        model = BudgetCommitment
        fields = (
            "number",
            "ped",
            "commitment_date",
            "initial_value",
            "source",
            "notes",
            "is_active",
        )
        widgets = {
            "commitment_date": _html_date_input(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "initial_value": "Reforços e anulações são registrados separadamente.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _localize_decimal_fields(self, "initial_value")


class CommitmentMovementForm(forms.ModelForm):
    class Meta:
        model = CommitmentMovement
        fields = (
            "movement_type",
            "movement_date",
            "amount",
            "document_reference",
            "notes",
        )
        widgets = {
            "movement_date": _html_date_input(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "amount": (
                "No estorno anual, informe exatamente o saldo disponível não "
                "comprometido constante no documento oficial."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _localize_decimal_fields(self, "amount")


class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = (
            "number",
            "item",
            "description",
            "quantity",
            "hours",
            "responsible",
            "opening_date",
            "signature_date",
            "start_date",
            "deadline",
            "monthly_follow_up",
            "completion_date",
            "status",
            "process_number",
            "notes",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "opening_date": _html_date_input(),
            "signature_date": _html_date_input(),
            "start_date": _html_date_input(),
            "deadline": _html_date_input(),
            "completion_date": _html_date_input(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "quantity": "Use para itens que não sejam medidos por hora.",
            "hours": "Use somente quando a unidade do item for Hora.",
            "item": "O valor unitário será copiado do item e não poderá ser digitado.",
            "status": "O cancelamento é realizado em ação própria, com motivo obrigatório.",
            "monthly_follow_up": (
                "Marque apenas quando a OS exigir atualização, medição ou "
                "faturamento mensal conforme fonte oficial. Itens com unidade Mês "
                "já entram no acompanhamento automaticamente."
            ),
        }

    def __init__(self, *args, contract, **kwargs):
        super().__init__(*args, **kwargs)
        self.contract = contract
        self.fields["item"].queryset = contract.items.filter(is_active=True)
        if self.instance.pk:
            self.fields["item"].queryset = contract.items.filter(
                pk__in=(self.instance.item_id,)
            ) | contract.items.filter(is_active=True)
            self.fields["item"].disabled = True
        self.fields["status"].choices = [
            choice for choice in WorkOrderStatus.choices
            if choice[0] != WorkOrderStatus.CANCELED
        ]
        _localize_decimal_fields(self, "quantity", "hours")

    def clean_item(self):
        item = self.cleaned_data["item"]
        if item.contract_id != self.contract.pk:
            raise forms.ValidationError("O item deve pertencer ao contrato da OS.")
        if not self.instance.pk:
            self.instance.unit_value = item.unit_value
            self.instance.unit_name = item.unit_display
        return item


class WorkOrderCancellationForm(forms.Form):
    reason = forms.CharField(
        label="Motivo do cancelamento",
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe o motivo do cancelamento.")
        return reason


class WorkOrderAllocationForm(forms.ModelForm):
    class Meta:
        model = WorkOrderAllocation
        fields = ("commitment", "amount", "allocation_date", "status")
        widgets = {"allocation_date": _html_date_input()}
        help_texts = {
            "amount": "O valor deve respeitar o saldo do empenho e o total da OS.",
            "status": "Use Cancelar para preservar motivo, autor e data do cancelamento.",
        }

    def __init__(self, *args, work_order, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_order = work_order
        queryset = work_order.contract.commitments.filter(
            is_active=True,
            closed_for_new_allocations_at__isnull=True,
        )
        if self.instance.pk:
            queryset = queryset | work_order.contract.commitments.filter(
                pk=self.instance.commitment_id
            )
        self.fields["commitment"].queryset = queryset.distinct()
        _localize_decimal_fields(self, "amount")
        self.fields["status"].choices = [
            choice for choice in WorkOrderAllocationStatus.choices
            if choice[0] != WorkOrderAllocationStatus.CANCELED
        ]

    def clean_commitment(self):
        commitment = self.cleaned_data["commitment"]
        if commitment.contract_id != self.work_order.contract_id:
            raise forms.ValidationError("O empenho deve pertencer ao contrato da OS.")
        return commitment


class WorkOrderAllocationCancellationForm(forms.Form):
    reason = forms.CharField(
        label="Motivo do cancelamento",
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    def clean_reason(self):
        reason = " ".join(self.cleaned_data["reason"].split())
        if not reason:
            raise forms.ValidationError("Informe o motivo do cancelamento.")
        return reason


class WorkOrderExecutionForm(forms.ModelForm):
    class Meta:
        model = WorkOrderExecution
        fields = (
            "executed_quantity",
            "executed_value",
            "execution_date",
            "competence",
            "notes",
            "evidence_reference",
        )
        widgets = {
            "execution_date": _html_date_input(),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "evidence_reference": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "executed_quantity": "Informe a quantidade ou as horas efetivamente executadas.",
            "executed_value": "Este valor permanece separado de faturamento e pagamento.",
            "competence": "Opcional. Use MM/AAAA quando aplicável.",
            "evidence_reference": "Opcional. Não anexe arquivo aqui; apenas identifique a evidência.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _localize_decimal_fields(self, "executed_quantity", "executed_value")


class InvoiceForm(forms.ModelForm):
    supplier_tax_id = tax_id_field(label="CNPJ/CPF")

    class Meta:
        model = Invoice
        fields = (
            "item",
            "allocation",
            "number",
            "series",
            "supplier_name",
            "supplier_tax_id",
            "issue_date",
            "competence",
            "gross_value",
            "deduction_value",
            "accepted_value",
            "process_number",
            "status",
            "document_reference",
            "document_hash",
            "notes",
        )
        widgets = {
            "issue_date": _html_date_input(),
            "document_reference": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        help_texts = {
            "item": "Opcional; quando informado, deve ser o item da OS.",
            "allocation": "Opcional; selecione somente um rateio da própria OS.",
            "competence": "Use MM/AAAA.",
            "status": "Informe exatamente o status constante na fonte. As opções oficiais ainda não foram definidas.",
            "accepted_value": "Não é calculado automaticamente: a fórmula oficial ainda depende de confirmação.",
            "document_reference": "Opcional. O upload protegido será implementado na Etapa 31.",
            "document_hash": "Opcional. SHA-256 com 64 caracteres hexadecimais.",
        }

    def __init__(self, *args, work_order, **kwargs):
        super().__init__(*args, **kwargs)
        self.work_order = work_order
        self.instance.contract = work_order.contract
        self.instance.work_order = work_order
        self.fields["item"].queryset = work_order.contract.items.filter(
            pk=work_order.item_id
        )
        self.fields["allocation"].queryset = work_order.allocations.all()
        if not self.is_bound and not self.instance.pk:
            self.initial["supplier_name"] = work_order.contract.supplier_name
            self.initial["supplier_tax_id"] = format_tax_id(work_order.contract.supplier_tax_id)
        elif not self.is_bound:
            self.initial["supplier_tax_id"] = format_tax_id(self.instance.supplier_tax_id)
        _localize_decimal_fields(
            self, "gross_value", "deduction_value", "accepted_value"
        )

    def clean_supplier_tax_id(self):
        return clean_tax_id(self.cleaned_data["supplier_tax_id"])


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = (
            "amount",
            "payment_date",
            "competence",
            "status",
            "process_number",
            "attestation_reference",
            "raer_reference",
            "homologation_reference",
            "evidence_reference",
            "notes",
        )
        widgets = {
            "payment_date": _html_date_input(),
            "attestation_reference": forms.Textarea(attrs={"rows": 2}),
            "raer_reference": forms.Textarea(attrs={"rows": 2}),
            "homologation_reference": forms.Textarea(attrs={"rows": 2}),
            "evidence_reference": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "competence": "Opcional. Use MM/AAAA quando aplicável.",
            "status": "Informe exatamente o status constante na fonte; não altera o cálculo.",
            "attestation_reference": "Obrigatório. Identifique o Atesto que fundamenta o pagamento.",
            "raer_reference": "Obrigatório. Identifique a RAER correspondente.",
            "homologation_reference": "Obrigatório. Identifique o Termo de Homologação.",
            "evidence_reference": "Opcional nesta etapa; identifique o comprovante, sem upload.",
        }

    def __init__(self, *args, invoice, **kwargs):
        super().__init__(*args, **kwargs)
        self.invoice = invoice
        self.instance.invoice = invoice
        _localize_decimal_fields(self, "amount")
