from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView

from .forms import (
    ContractAlertPolicyForm,
    ContractChangeForm,
    ContractChangeVoidForm,
    ContractChecklistItemForm,
    ContractExternalRecordForm,
    ContractObligationForm,
    ContractReceiptForm,
    ContractRiskForm,
)
from .governance import (
    apply_control_pack,
    contract_governance_counts,
    create_contract_change,
    create_external_record,
    create_obligation,
    create_receipt,
    create_risk,
    governance_snapshot,
    update_alert_policy,
    update_checklist_item,
    update_external_record,
    update_obligation,
    update_risk,
    void_contract_change,
)
from .models import (
    Contract,
    ContractChange,
    ContractChecklistItem,
    ContractExternalRecord,
    ContractObligation,
    ContractRisk,
)
from .services import contracts_visible_to, contracts_writable_by


class GovernanceContractMixin(LoginRequiredMixin):
    contract = None

    def dispatch(self, request, *args, **kwargs):
        self.contract = get_object_or_404(
            contracts_visible_to(request.user), pk=kwargs["contract_pk"]
        )
        if not contracts_writable_by(request.user).filter(
            pk=self.contract.pk
        ).exists():
            raise PermissionDenied("Somente o Fiscal autorizado pode alterar a governança.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse("contracts:governance", args=[self.contract.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.contract
        return context


class ContractGovernanceView(LoginRequiredMixin, DetailView):
    model = Contract
    context_object_name = "contract"
    template_name = "contracts/contract_governance.html"
    pk_url_kwarg = "contract_pk"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(governance_snapshot(self.object, self.request.user))
        context["governance_counts"] = contract_governance_counts(
            self.object,
            auxiliary=context["limited_auxiliary"],
        )
        return context


class GovernanceFormView(GovernanceContractMixin, FormView):
    template_name = "contracts/governance_form.html"
    heading = "Governança contratual"
    submit_label = "Salvar"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["heading"] = self.heading
        context["submit_label"] = self.submit_label
        return context


class ContractAlertPolicyUpdateView(GovernanceFormView):
    form_class = ContractAlertPolicyForm
    heading = "Política de alertas de vigência"
    submit_label = "Atualizar alertas"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["policy"] = getattr(self.contract, "alert_policy", None)
        return kwargs

    def form_valid(self, form):
        update_alert_policy(
            contract_id=self.contract.pk,
            actor=self.request.user,
            days=form.cleaned_data["validity_warning_days"],
        )
        messages.success(self.request, "Política de alertas atualizada com rastreabilidade.")
        return redirect(self.get_success_url())


class ContractObligationCreateView(GovernanceFormView):
    form_class = ContractObligationForm
    heading = "Cadastrar obrigação contratual"

    def form_valid(self, form):
        create_obligation(
            contract_id=self.contract.pk, actor=self.request.user, data=form.cleaned_data
        )
        messages.success(self.request, "Obrigação cadastrada.")
        return redirect(self.get_success_url())


class ContractObligationUpdateView(GovernanceFormView):
    form_class = ContractObligationForm
    heading = "Atualizar obrigação contratual"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(
            ContractObligation, pk=self.kwargs["pk"], contract=self.contract
        )
        return kwargs

    def form_valid(self, form):
        update_obligation(
            obligation_id=self.kwargs["pk"], contract_id=self.contract.pk,
            actor=self.request.user, data=form.cleaned_data,
        )
        messages.success(self.request, "Obrigação atualizada.")
        return redirect(self.get_success_url())


class ContractChangeCreateView(GovernanceFormView):
    form_class = ContractChangeForm
    heading = "Registrar alteração contratual"
    submit_label = "Registrar instrumento"

    def form_valid(self, form):
        data = dict(form.cleaned_data)
        data.pop("confirmed", None)
        create_contract_change(
            contract_id=self.contract.pk, actor=self.request.user, data=data
        )
        messages.success(self.request, "Alteração registrada e valor atual recalculado.")
        return redirect(self.get_success_url())


class ContractChangeVoidView(GovernanceFormView):
    form_class = ContractChangeVoidForm
    heading = "Anular alteração contratual"
    submit_label = "Confirmar anulação"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["change"] = get_object_or_404(
            ContractChange, pk=self.kwargs["pk"], contract=self.contract
        )
        return context

    def form_valid(self, form):
        void_contract_change(
            change_id=self.kwargs["pk"], contract_id=self.contract.pk,
            actor=self.request.user, reason=form.cleaned_data["reason"],
        )
        messages.success(self.request, "Alteração anulada sem apagar o histórico.")
        return redirect(self.get_success_url())


class ContractReceiptCreateView(GovernanceFormView):
    form_class = ContractReceiptForm
    heading = "Registrar recebimento"

    def form_valid(self, form):
        create_receipt(
            contract_id=self.contract.pk, actor=self.request.user, data=form.cleaned_data
        )
        messages.success(self.request, "Recebimento registrado.")
        return redirect(self.get_success_url())


class ContractRiskCreateView(GovernanceFormView):
    form_class = ContractRiskForm
    heading = "Cadastrar risco contratual"

    def form_valid(self, form):
        create_risk(
            contract_id=self.contract.pk, actor=self.request.user, data=form.cleaned_data
        )
        messages.success(self.request, "Risco cadastrado.")
        return redirect(self.get_success_url())


class ContractRiskUpdateView(GovernanceFormView):
    form_class = ContractRiskForm
    heading = "Atualizar risco contratual"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(
            ContractRisk, pk=self.kwargs["pk"], contract=self.contract
        )
        return kwargs

    def form_valid(self, form):
        update_risk(
            risk_id=self.kwargs["pk"], contract_id=self.contract.pk,
            actor=self.request.user, data=form.cleaned_data,
        )
        messages.success(self.request, "Risco atualizado.")
        return redirect(self.get_success_url())


class ContractControlPackApplyView(GovernanceContractMixin, View):
    http_method_names = ("post",)

    def post(self, request, *args, **kwargs):
        if request.POST.get("confirm") != "APLICAR":
            raise ValidationError("Confirmação do pacote ausente.")
        pack, created = apply_control_pack(
            contract_id=self.contract.pk, actor=request.user,
            pack_code=kwargs["pack_code"],
        )
        messages.success(
            request,
            f"Pacote {pack.title} aplicado: {created} verificações novas, sempre a confirmar.",
        )
        return redirect(self.get_success_url())


class ContractChecklistItemUpdateView(GovernanceFormView):
    form_class = ContractChecklistItemForm
    heading = "Atualizar verificação do checklist"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(
            ContractChecklistItem, pk=self.kwargs["pk"], contract=self.contract
        )
        return kwargs

    def form_valid(self, form):
        update_checklist_item(
            item_id=self.kwargs["pk"], contract_id=self.contract.pk,
            actor=self.request.user, data=form.cleaned_data,
        )
        messages.success(self.request, "Checklist atualizado.")
        return redirect(self.get_success_url())


class ContractExternalRecordCreateView(GovernanceFormView):
    form_class = ContractExternalRecordForm
    heading = "Cadastrar acompanhamento em sistema oficial"

    def form_valid(self, form):
        create_external_record(
            contract_id=self.contract.pk, actor=self.request.user, data=form.cleaned_data
        )
        messages.success(self.request, "Acompanhamento oficial cadastrado.")
        return redirect(self.get_success_url())


class ContractExternalRecordUpdateView(GovernanceFormView):
    form_class = ContractExternalRecordForm
    heading = "Atualizar acompanhamento em sistema oficial"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = get_object_or_404(
            ContractExternalRecord, pk=self.kwargs["pk"], contract=self.contract
        )
        return kwargs

    def form_valid(self, form):
        update_external_record(
            record_id=self.kwargs["pk"], contract_id=self.contract.pk,
            actor=self.request.user, data=form.cleaned_data,
        )
        messages.success(self.request, "Acompanhamento oficial atualizado.")
        return redirect(self.get_success_url())
