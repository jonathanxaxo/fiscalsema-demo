from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView, UpdateView

from .forms import (
    AccountabilityFilterForm,
    ReportFilterForm,
    BudgetCommitmentForm,
    CommitmentMovementForm,
    ContractArchiveForm,
    ContractCloseForm,
    ContractForm,
    ContractShareForm,
    ContractRestoreForm,
    ContractTransferForm,
    FiscalSubstitutionForm,
    ContractItemForm,
    InvoiceForm,
    PaymentForm,
    WorkOrderCancellationForm,
    WorkOrderAllocationCancellationForm,
    WorkOrderAllocationForm,
    WorkOrderExecutionForm,
    WorkOrderForm,
)
from .accountability import build_accountability_snapshot
from .dashboard import build_contract_dashboard
from .executive_dashboard import build_executive_summary, build_monthly_evolution, build_validity_progress
from .exports import build_contract_csv, filters_for_audit
from .reports import build_contract_report
from .models import (
    BudgetCommitment,
    Contract,
    CsvExportEvent,
    ContractAccess,
    ContractInvitation,
    ContractItem,
    FiscalSubstitution,
    FiscalSubstitutionStatus,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderAllocation,
    WorkOrderAllocationStatus,
    WorkOrderExecution,
    WorkOrderStatus,
)
from .services import (
    actor_is_active_fiscal,
    archive_contract,
    archived_contracts_managed_by,
    allocations_visible_to,
    allocations_writable_by,
    cancel_work_order_allocation,
    commitment_financial_position,
    commitments_visible_to,
    commitments_writable_by,
    contract_financial_position,
    contracts_visible_to,
    contracts_exportable_by,
    contracts_lifecycle_managed_by,
    contracts_managed_by,
    contracts_with_access_management_visible_to,
    contracts_writable_by,
    contract_is_read_only_for,
    contract_operational_blockers,
    close_contract,
    cancel_contract_invitation,
    cancelable_invitations_by,
    cancel_work_order,
    create_budget_commitment,
    create_commitment_movement,
    create_contract,
    create_contract_item,
    create_fiscal_substitution,
    share_contract_read_only,
    revoke_contract_access,
    revocable_accesses_by,
    revocable_fiscal_substitutions_by,
    revoke_fiscal_substitution,
    restore_archived_contract,
    create_invoice,
    create_payment,
    create_work_order,
    create_work_order_allocation,
    create_work_order_execution,
    executions_writable_by,
    invoices_visible_to,
    invoices_writable_by,
    payments_visible_to,
    payments_writable_by,
    invoice_check_report,
    invoice_payment_position,
    items_visible_to,
    items_writable_by,
    item_financial_position,
    update_work_order,
    update_work_order_allocation,
    update_work_order_execution,
    update_budget_commitment,
    update_contract,
    transfer_contract_responsibility,
    update_contract_item,
    update_invoice,
    update_payment,
    work_order_invoice_position,
    work_orders_visible_to,
    work_orders_writable_by,
)


TABLE_MODE_OPTIONS = (
    ("items", "Itens"),
    ("commitments", "Empenhos"),
    ("work_orders", "Ordens de Serviço"),
    ("allocations", "Rateios"),
    ("invoices", "Notas fiscais"),
)

TABLE_MODE_ORDERINGS = {
    "items": (
        ("number", "Número crescente"),
        ("-number", "Número decrescente"),
        ("description", "Descrição"),
        ("unit_value", "Menor valor unitário"),
        ("-unit_value", "Maior valor unitário"),
    ),
    "commitments": (
        ("commitment_date", "Data crescente"),
        ("-commitment_date", "Data decrescente"),
        ("number", "Número"),
        ("initial_value", "Menor valor inicial"),
        ("-initial_value", "Maior valor inicial"),
    ),
    "work_orders": (
        ("opening_date", "Abertura crescente"),
        ("-opening_date", "Abertura decrescente"),
        ("number", "Número"),
        ("deadline", "Prazo crescente"),
        ("-deadline", "Prazo decrescente"),
        ("status", "Status"),
    ),
    "allocations": (
        ("allocation_date", "Data crescente"),
        ("-allocation_date", "Data decrescente"),
        ("work_order__number", "OS"),
        ("commitment__number", "Empenho"),
        ("amount", "Menor valor"),
        ("-amount", "Maior valor"),
    ),
    "invoices": (
        ("issue_date", "Emissão crescente"),
        ("-issue_date", "Emissão decrescente"),
        ("number", "Número"),
        ("gross_value", "Menor valor bruto"),
        ("-gross_value", "Maior valor bruto"),
        ("status", "Status informado"),
    ),
}


class ContractListView(LoginRequiredMixin, ListView):
    model = Contract
    context_object_name = "contracts"
    template_name = "contracts/contract_list.html"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = (
            actor_is_active_fiscal(self.request.user)
            and self.request.user.has_perm("contracts.add_contract")
            and bool(self.request.user.organization_id)
            and self.request.user.organization.is_active
        )
        context["read_only_contract_ids"] = set(
            ContractAccess.objects.filter(
                user=self.request.user, status="ATIVO", access_type="READ_ONLY"
            ).values_list("contract_id", flat=True)
        )
        today = timezone.localdate()
        context["substitute_contract_ids"] = set(
            FiscalSubstitution.objects.filter(
                substitute=self.request.user,
                status=FiscalSubstitutionStatus.LINKED,
                starts_on__lte=today,
                ends_on__gte=today,
            ).values_list("contract_id", flat=True)
        )
        return context


class ArchivedContractListView(LoginRequiredMixin, ListView):
    model = Contract
    context_object_name = "contracts"
    template_name = "contracts/contract_archived_list.html"

    def get_queryset(self):
        return archived_contracts_managed_by(self.request.user)


class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    context_object_name = "contract"
    template_name = "contracts/contract_detail.html"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = contracts_writable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context["financial_position"] = contract_financial_position(self.object)
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.object
        )
        context["can_manage_access"] = contracts_with_access_management_visible_to(
            self.request.user
        ).filter(pk=self.object.pk).exists()
        context["can_export"] = contracts_exportable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context["can_manage_lifecycle"] = (
            contracts_lifecycle_managed_by(self.request.user)
            .exclude(status__in=("ENCERRADO", "CANCELADO"))
            .filter(pk=self.object.pk)
            .exists()
        )
        context["structural_fields_locked"] = bool(
            contract_operational_blockers(self.object)
        )
        return context


class ContractDashboardView(LoginRequiredMixin, DetailView):
    model = Contract
    context_object_name = "selected_contract"
    template_name = "home.html"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_write = contracts_writable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context.update(
            {
                "contracts": (self.object,),
                "dashboard": build_contract_dashboard(self.object),
                "pending_registration_count": 0,
                "can_create_contract": False,
                "can_create_item": can_write,
                "is_read_only_access": contract_is_read_only_for(
                    self.request.user, self.object
                ),
                "is_substitute_access": (
                    can_write
                    and self.object.responsible_fiscal_id != self.request.user.pk
                ),
                "contract_dashboard_mode": True,
            }
        )
        return context


class AccountabilityView(LoginRequiredMixin, DetailView):
    model = Contract
    pk_url_kwarg = "contract_pk"
    context_object_name = "contract"
    template_name = "contracts/accountability.html"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = AccountabilityFilterForm(self.request.GET or None, contract=self.object)
        filters = form.cleaned_data if form.is_valid() else {}
        context["filter_form"] = form
        context["accountability"] = build_accountability_snapshot(
            self.object, filters
        )
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.object
        )
        context["can_export"] = contracts_exportable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context["export_query"] = self.request.GET.urlencode()
        return context


class ContractReportView(LoginRequiredMixin, DetailView):
    model = Contract
    pk_url_kwarg = "contract_pk"
    context_object_name = "contract"
    template_name = "contracts/report.html"

    def get_queryset(self):
        return contracts_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ReportFilterForm(self.request.GET or None, contract=self.object)
        filters = form.cleaned_data if form.is_valid() else {}
        context["filter_form"] = form
        context["report"] = build_contract_report(self.object, filters)
        context["print_mode"] = self.request.GET.get("print") == "1"
        query = self.request.GET.copy()
        query["print"] = "1"
        context["print_query"] = query.urlencode()
        query.pop("print", None)
        context["export_query"] = query.urlencode()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.object
        )
        context["can_export"] = contracts_exportable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        return context


class ContractCsvExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        contract = get_object_or_404(
            contracts_exportable_by(request.user), pk=kwargs["contract_pk"]
        )
        form = ReportFilterForm(request.GET, contract=contract)
        if not form.is_valid():
            return HttpResponseBadRequest(
                "Filtros inválidos. Revise período, competência e registros selecionados."
            )
        filters = form.cleaned_data
        export = build_contract_csv(build_contract_report(contract, filters))
        file_name = (
            f"fiscalsema-contrato-{contract.pk}-"
            f"{timezone.localdate().isoformat()}.csv"
        )
        CsvExportEvent.objects.create(
            contract=contract,
            actor=request.user,
            details={
                "arquivo": file_name,
                "formato": "CSV UTF-8",
                "delimitador": ";",
                "linhas": export.row_count,
                "filtros": filters_for_audit(filters),
            },
        )
        response = HttpResponse(export.content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response


class ContractAccessListView(LoginRequiredMixin, DetailView):
    model = Contract
    pk_url_kwarg = "contract_pk"
    context_object_name = "contract"
    template_name = "contracts/access_list.html"

    def get_queryset(self):
        return contracts_with_access_management_visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accesses"] = self.object.accesses.select_related(
            "user", "granted_by", "revoked_by"
        )
        context["invitations"] = self.object.invitations.select_related(
            "invited_by", "accepted_by"
        )
        context["substitutions"] = self.object.fiscal_substitutions.select_related(
            "substitute", "created_by", "revoked_by"
        )
        context["can_share"] = contracts_managed_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context["can_create_substitution"] = context["can_share"]
        context["revocable_access_ids"] = set(
            revocable_accesses_by(self.request.user)
            .filter(contract=self.object)
            .values_list("pk", flat=True)
        )
        context["cancelable_invitation_ids"] = set(
            cancelable_invitations_by(self.request.user)
            .filter(contract=self.object)
            .values_list("pk", flat=True)
        )
        context["revocable_substitution_ids"] = set(
            revocable_fiscal_substitutions_by(self.request.user)
            .filter(contract=self.object)
            .values_list("pk", flat=True)
        )
        return context


class ContractShareView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractShareForm
    template_name = "contracts/access_share.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_managed_by(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return contracts_managed_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.get_contract()
        )
        return context

    def form_valid(self, form):
        try:
            access, invitation = share_contract_read_only(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                email=form.cleaned_data["email"],
                confirm_regrant=form.cleaned_data["confirm_regrant"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if access:
            messages.success(
                self.request,
                "Acesso Somente leitura concedido ou reativado para a conta existente.",
            )
        else:
            messages.success(
                self.request,
                "Convite registrado. O envio por e-mail depende do SMTP institucional.",
            )
        return redirect("contracts:access_list", contract_pk=self.get_contract().pk)


class FiscalSubstitutionCreateView(
    LoginRequiredMixin, UserPassesTestMixin, FormView
):
    form_class = FiscalSubstitutionForm
    template_name = "contracts/fiscal_substitution_form.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_managed_by(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return contracts_managed_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        return context

    def form_valid(self, form):
        try:
            substitution = create_fiscal_substitution(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                email=form.cleaned_data["email"],
                starts_on=form.cleaned_data["starts_on"],
                ends_on=form.cleaned_data["ends_on"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if substitution.status == FiscalSubstitutionStatus.LINKED:
            messages.success(
                self.request,
                "Fiscal substituto vinculado. O acesso valerá somente no período informado.",
            )
        else:
            messages.success(
                self.request,
                "Substituição registrada e aguardando cadastro e aprovação da conta.",
            )
        return redirect("contracts:access_list", contract_pk=self.get_contract().pk)


class FiscalSubstitutionRevokeView(LoginRequiredMixin, DetailView):
    model = FiscalSubstitution
    pk_url_kwarg = "substitution_pk"
    context_object_name = "substitution"
    template_name = "contracts/fiscal_substitution_revoke_confirm.html"

    def get_queryset(self):
        return revocable_fiscal_substitutions_by(self.request.user).filter(
            contract_id=self.kwargs["contract_pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.object.contract
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        revoke_fiscal_substitution(
            substitution_id=self.object.pk,
            contract_id=self.object.contract_id,
            actor=request.user,
        )
        messages.success(request, "Substituição revogada. O efeito é imediato.")
        return redirect("contracts:access_list", contract_pk=self.object.contract_id)


class ContractAccessRevokeView(LoginRequiredMixin, DetailView):
    model = ContractAccess
    pk_url_kwarg = "access_pk"
    context_object_name = "access"
    template_name = "contracts/access_revoke_confirm.html"

    def get_queryset(self):
        return revocable_accesses_by(self.request.user).filter(
            contract_id=self.kwargs["contract_pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.object.contract
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        revoke_contract_access(
            access_id=self.object.pk,
            contract_id=self.object.contract_id,
            actor=request.user,
        )
        messages.success(request, "Acesso revogado. O efeito é imediato.")
        return redirect("contracts:access_list", contract_pk=self.object.contract_id)


class ContractInvitationCancelView(LoginRequiredMixin, DetailView):
    model = ContractInvitation
    pk_url_kwarg = "invitation_pk"
    context_object_name = "invitation"
    template_name = "contracts/invitation_cancel_confirm.html"

    def get_queryset(self):
        return cancelable_invitations_by(self.request.user).filter(
            contract_id=self.kwargs["contract_pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.object.contract
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        cancel_contract_invitation(
            invitation_id=self.object.pk,
            contract_id=self.object.contract_id,
            actor=request.user,
        )
        messages.success(request, "Convite pendente cancelado com histórico preservado.")
        return redirect("contracts:access_list", contract_pk=self.object.contract_id)


class ContractTableModeView(LoginRequiredMixin, TemplateView):
    template_name = "contracts/table_mode.html"
    page_size = 25

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_visible_to(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def get_table_type(self):
        requested = self.request.GET.get("tipo", "items")
        return requested if requested in dict(TABLE_MODE_OPTIONS) else "items"

    def get_queryset_for_table(self, table_type, query):
        contract = self.get_contract()
        if table_type == "items":
            queryset = items_visible_to(self.request.user).filter(contract=contract)
            if query:
                queryset = queryset.filter(
                    Q(number__icontains=query)
                    | Q(description__icontains=query)
                    | Q(category__icontains=query)
                    | Q(custom_unit_name__icontains=query)
                )
        elif table_type == "commitments":
            queryset = commitments_visible_to(self.request.user).filter(contract=contract)
            if query:
                queryset = queryset.filter(
                    Q(number__icontains=query)
                    | Q(ped__icontains=query)
                    | Q(source__icontains=query)
                )
        elif table_type == "work_orders":
            queryset = work_orders_visible_to(self.request.user).filter(
                contract=contract
            ).prefetch_related("allocations__commitment", "invoices")
            if query:
                queryset = queryset.filter(
                    Q(number__icontains=query)
                    | Q(item__number__icontains=query)
                    | Q(description__icontains=query)
                    | Q(responsible__icontains=query)
                    | Q(process_number__icontains=query)
                    | Q(status__icontains=query)
                )
        elif table_type == "allocations":
            queryset = allocations_visible_to(self.request.user).filter(
                work_order__contract=contract
            )
            if query:
                queryset = queryset.filter(
                    Q(work_order__number__icontains=query)
                    | Q(commitment__number__icontains=query)
                    | Q(status__icontains=query)
                )
        else:
            queryset = invoices_visible_to(self.request.user).filter(contract=contract)
            if query:
                queryset = queryset.filter(
                    Q(number__icontains=query)
                    | Q(series__icontains=query)
                    | Q(work_order__number__icontains=query)
                    | Q(supplier_name__icontains=query)
                    | Q(competence__icontains=query)
                    | Q(process_number__icontains=query)
                    | Q(status__icontains=query)
                )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        table_type = self.get_table_type()
        query = self.request.GET.get("q", "").strip()[:200]
        ordering_options = TABLE_MODE_ORDERINGS[table_type]
        allowed_orderings = {value for value, _ in ordering_options}
        ordering = self.request.GET.get("ordenar", ordering_options[0][0])
        if ordering not in allowed_orderings:
            ordering = ordering_options[0][0]
        queryset = self.get_queryset_for_table(table_type, query).order_by(ordering, "pk")
        page = Paginator(queryset, self.page_size).get_page(self.request.GET.get("pagina"))
        if table_type == "commitments":
            for commitment in page.object_list:
                commitment.table_position = commitment_financial_position(commitment)
        contract = self.get_contract()
        context.update(
            {
                "contract": contract,
                "table_options": TABLE_MODE_OPTIONS,
                "selected_type": table_type,
                "ordering_options": ordering_options,
                "selected_ordering": ordering,
                "query": query,
                "page_obj": page,
                "rows": page.object_list,
                "can_write": contracts_writable_by(self.request.user)
                .filter(pk=contract.pk)
                .exists(),
                "is_read_only_access": contract_is_read_only_for(
                    self.request.user, contract
                ),
            }
        )
        return context


class ContractCreateView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractForm
    template_name = "contracts/contract_form.html"
    raise_exception = True

    def test_func(self):
        return (
            actor_is_active_fiscal(self.request.user)
            and self.request.user.has_perm("contracts.add_contract")
            and bool(self.request.user.organization_id)
            and self.request.user.organization.is_active
        )

    def form_valid(self, form):
        try:
            contract = create_contract(actor=self.request.user, **form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Contrato criado com sucesso.")
        return redirect("contracts:detail", pk=contract.pk)


class ContractUpdateView(LoginRequiredMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = "contracts/contract_form.html"

    def get_queryset(self):
        return contracts_writable_by(self.request.user)

    def form_valid(self, form):
        try:
            contract = update_contract(
                contract_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Contrato atualizado com sucesso.")
        return redirect("contracts:detail", pk=contract.pk)


class ContractCloseView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractCloseForm
    template_name = "contracts/contract_close_form.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_lifecycle_managed_by(self.request.user).exclude(
                    status__in=("ENCERRADO", "CANCELADO")
                ),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return (
            contracts_lifecycle_managed_by(self.request.user)
            .exclude(status__in=("ENCERRADO", "CANCELADO"))
            .filter(pk=self.kwargs["contract_pk"])
            .exists()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        return context

    def form_valid(self, form):
        try:
            contract = close_contract(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                reason=form.cleaned_data["reason"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            "Contrato encerrado. O histórico permanece disponível somente para consulta.",
        )
        return redirect("contracts:detail", pk=contract.pk)


class ContractTransferView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractTransferForm
    template_name = "contracts/contract_transfer_form.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_lifecycle_managed_by(self.request.user).exclude(
                    status__in=("ENCERRADO", "CANCELADO")
                ),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return (
            contracts_lifecycle_managed_by(self.request.user)
            .exclude(status__in=("ENCERRADO", "CANCELADO"))
            .filter(pk=self.kwargs["contract_pk"])
            .exists()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        return context

    def form_valid(self, form):
        try:
            contract = transfer_contract_responsibility(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                email=form.cleaned_data["email"],
                reason=form.cleaned_data["reason"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Responsabilidade do contrato transferida com sucesso.")
        return redirect("contracts:list")


class ContractArchiveView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractArchiveForm
    template_name = "contracts/contract_archive_form.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_lifecycle_managed_by(self.request.user).exclude(
                    status__in=("ENCERRADO", "CANCELADO")
                ),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return (
            contracts_lifecycle_managed_by(self.request.user)
            .exclude(status__in=("ENCERRADO", "CANCELADO"))
            .filter(pk=self.kwargs["contract_pk"])
            .exists()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["blockers"] = contract_operational_blockers(
            self.get_contract(), include_active_accesses=True
        )
        return context

    def form_valid(self, form):
        try:
            archive_contract(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                reason=form.cleaned_data["reason"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            "Contrato arquivado logicamente. O histórico foi preservado.",
        )
        return redirect("contracts:list")


class ContractRestoreView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = ContractRestoreForm
    template_name = "contracts/contract_restore_form.html"
    raise_exception = True

    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                archived_contracts_managed_by(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def test_func(self):
        return archived_contracts_managed_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        return context

    def form_valid(self, form):
        try:
            contract = restore_archived_contract(
                contract_id=self.get_contract().pk,
                actor=self.request.user,
                reason=form.cleaned_data["reason"],
                confirmed=form.cleaned_data["confirmed"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Contrato restaurado com auditoria preservada.")
        return redirect("contracts:detail", pk=contract.pk)


class ContractItemContextMixin(LoginRequiredMixin):
    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_visible_to(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.get_contract()
        )
        return context


class ContractItemListView(ContractItemContextMixin, ListView):
    model = ContractItem
    context_object_name = "items"
    template_name = "contracts/item_list.html"

    def get_queryset(self):
        return items_visible_to(self.request.user).filter(contract=self.get_contract())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = contracts_writable_by(self.request.user).filter(
            pk=self.get_contract().pk
        ).exists()
        return context


class ContractItemDetailView(ContractItemContextMixin, DetailView):
    model = ContractItem
    context_object_name = "item"
    template_name = "contracts/item_detail.html"

    def get_queryset(self):
        return items_visible_to(self.request.user).filter(contract=self.get_contract())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = items_writable_by(self.request.user).filter(
            pk=self.object.pk
        ).exists()
        context["financial_position"] = item_financial_position(self.object)
        return context


class ContractItemCreateView(ContractItemContextMixin, UserPassesTestMixin, FormView):
    form_class = ContractItemForm
    template_name = "contracts/item_form.html"
    raise_exception = True

    def test_func(self):
        return contracts_writable_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def form_valid(self, form):
        try:
            item = create_contract_item(
                contract_id=self.kwargs["contract_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Item contratual criado com sucesso.")
        return redirect(
            "contracts:item_detail",
            contract_pk=item.contract_id,
            pk=item.pk,
        )


class ContractItemUpdateView(ContractItemContextMixin, UpdateView):
    model = ContractItem
    form_class = ContractItemForm
    template_name = "contracts/item_form.html"

    def get_queryset(self):
        return items_writable_by(self.request.user).filter(contract=self.get_contract())

    def form_valid(self, form):
        item = update_contract_item(
            item_id=self.object.pk,
            actor=self.request.user,
            **form.cleaned_data,
        )
        messages.success(self.request, "Item contratual atualizado com sucesso.")
        return redirect(
            "contracts:item_detail",
            contract_pk=item.contract_id,
            pk=item.pk,
        )


class BudgetCommitmentContextMixin(LoginRequiredMixin):
    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_visible_to(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.get_contract()
        )
        return context


class BudgetCommitmentListView(BudgetCommitmentContextMixin, ListView):
    model = BudgetCommitment
    context_object_name = "commitments"
    template_name = "contracts/commitment_list.html"

    def get_queryset(self):
        return commitments_visible_to(self.request.user).filter(
            contract=self.get_contract()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = contracts_writable_by(self.request.user).filter(
            pk=self.get_contract().pk
        ).exists()
        return context


class BudgetCommitmentDetailView(BudgetCommitmentContextMixin, DetailView):
    model = BudgetCommitment
    context_object_name = "commitment"
    template_name = "contracts/commitment_detail.html"

    def get_queryset(self):
        return commitments_visible_to(self.request.user).filter(
            contract=self.get_contract()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        writable = commitments_writable_by(self.request.user).filter(pk=self.object.pk)
        context["can_edit"] = writable.exists()
        context["can_add_movement"] = (
            self.object.accepts_new_allocations and writable.exists()
        )
        context["financial_position"] = commitment_financial_position(self.object)
        return context


class BudgetCommitmentCreateView(
    BudgetCommitmentContextMixin,
    UserPassesTestMixin,
    FormView,
):
    form_class = BudgetCommitmentForm
    template_name = "contracts/commitment_form.html"
    raise_exception = True

    def test_func(self):
        return contracts_writable_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def form_valid(self, form):
        try:
            commitment = create_budget_commitment(
                contract_id=self.kwargs["contract_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Empenho criado com sucesso.")
        return redirect(
            "contracts:commitment_detail",
            contract_pk=commitment.contract_id,
            pk=commitment.pk,
        )


class BudgetCommitmentUpdateView(BudgetCommitmentContextMixin, UpdateView):
    model = BudgetCommitment
    form_class = BudgetCommitmentForm
    template_name = "contracts/commitment_form.html"

    def get_queryset(self):
        return commitments_writable_by(self.request.user).filter(
            contract=self.get_contract()
        )

    def form_valid(self, form):
        try:
            commitment = update_budget_commitment(
                commitment_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Empenho atualizado com sucesso.")
        return redirect(
            "contracts:commitment_detail",
            contract_pk=commitment.contract_id,
            pk=commitment.pk,
        )


class CommitmentMovementCreateView(
    BudgetCommitmentContextMixin,
    UserPassesTestMixin,
    FormView,
):
    form_class = CommitmentMovementForm
    template_name = "contracts/commitment_movement_form.html"
    raise_exception = True

    def get_commitment(self):
        if not hasattr(self, "commitment"):
            self.commitment = get_object_or_404(
                commitments_writable_by(self.request.user).filter(
                    contract=self.get_contract(),
                    is_active=True,
                ),
                pk=self.kwargs["commitment_pk"],
            )
        return self.commitment

    def test_func(self):
        return (
            self.request.user.has_perm("contracts.add_commitmentmovement")
            and commitments_writable_by(self.request.user).filter(
                pk=self.kwargs["commitment_pk"],
                contract_id=self.kwargs["contract_pk"],
                is_active=True,
            ).exists()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["commitment"] = self.get_commitment()
        return context

    def form_valid(self, form):
        try:
            movement = create_commitment_movement(
                commitment_id=self.kwargs["commitment_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Movimentação registrada com sucesso.")
        return redirect(
            "contracts:commitment_detail",
            contract_pk=movement.commitment.contract_id,
            pk=movement.commitment_id,
        )


class WorkOrderContextMixin(LoginRequiredMixin):
    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_visible_to(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.get_contract()
        )
        return context


class WorkOrderListView(WorkOrderContextMixin, ListView):
    model = WorkOrder
    context_object_name = "work_orders"
    template_name = "contracts/work_order_list.html"

    def get_queryset(self):
        return work_orders_visible_to(self.request.user).filter(
            contract=self.get_contract()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_create"] = contracts_writable_by(self.request.user).filter(
            pk=self.get_contract().pk
        ).exists()
        return context


class WorkOrderDetailView(WorkOrderContextMixin, DetailView):
    model = WorkOrder
    context_object_name = "work_order"
    template_name = "contracts/work_order_detail.html"

    def get_queryset(self):
        return work_orders_visible_to(self.request.user).filter(
            contract=self.get_contract()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        writable = work_orders_writable_by(self.request.user).filter(pk=self.object.pk)
        context["can_edit"] = (
            self.object.status != WorkOrderStatus.CANCELED and writable.exists()
        )
        context["can_cancel"] = context["can_edit"]
        context["can_add_allocation"] = (
            self.object.status != WorkOrderStatus.CANCELED and writable.exists()
        )
        context["can_add_execution"] = (
            self.object.status != WorkOrderStatus.CANCELED
            and writable.exists()
            and self.request.user.has_perm("contracts.add_workorderexecution")
        )
        context["active_allocated"] = sum(
            (
                allocation.amount
                for allocation in self.object.allocations.filter(
                    status=WorkOrderAllocationStatus.ACTIVE
                )
            ),
            0,
        )
        context["allocation_balance"] = (
            self.object.total_value - context["active_allocated"]
        )
        context["executed_quantity"] = sum(
            self.object.executions.values_list("executed_quantity", flat=True), 0
        )
        context["executed_value"] = sum(
            self.object.executions.values_list("executed_value", flat=True), 0
        )
        context["execution_quantity_balance"] = (
            self.object.measure - context["executed_quantity"]
        )
        context["execution_value_balance"] = (
            self.object.total_value - context["executed_value"]
        )
        context["invoice_position"] = work_order_invoice_position(self.object)
        context["can_add_invoice"] = (
            self.object.status != WorkOrderStatus.CANCELED
            and writable.exists()
            and self.request.user.has_perm("contracts.add_invoice")
        )
        return context


class WorkOrderCreateView(WorkOrderContextMixin, UserPassesTestMixin, FormView):
    form_class = WorkOrderForm
    template_name = "contracts/work_order_form.html"
    raise_exception = True

    def test_func(self):
        return contracts_writable_by(self.request.user).filter(
            pk=self.kwargs["contract_pk"]
        ).exists()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["contract"] = self.get_contract()
        return kwargs

    def form_valid(self, form):
        try:
            work_order = create_work_order(
                contract_id=self.kwargs["contract_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Ordem de serviço criada com sucesso.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=work_order.contract_id,
            pk=work_order.pk,
        )


class WorkOrderUpdateView(WorkOrderContextMixin, UpdateView):
    model = WorkOrder
    form_class = WorkOrderForm
    template_name = "contracts/work_order_form.html"

    def get_queryset(self):
        return work_orders_writable_by(self.request.user).exclude(
            status=WorkOrderStatus.CANCELED
        ).filter(contract=self.get_contract())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["contract"] = self.get_contract()
        return kwargs

    def form_valid(self, form):
        try:
            work_order = update_work_order(
                work_order_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Ordem de serviço atualizada com sucesso.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=work_order.contract_id,
            pk=work_order.pk,
        )


class WorkOrderCancelView(WorkOrderContextMixin, UserPassesTestMixin, FormView):
    form_class = WorkOrderCancellationForm
    template_name = "contracts/work_order_cancel.html"
    raise_exception = True

    def get_work_order(self):
        if not hasattr(self, "work_order"):
            self.work_order = get_object_or_404(
                work_orders_writable_by(self.request.user).exclude(
                    status=WorkOrderStatus.CANCELED
                ).filter(contract=self.get_contract()),
                pk=self.kwargs["pk"],
            )
        return self.work_order

    def test_func(self):
        return work_orders_writable_by(self.request.user).exclude(
            status=WorkOrderStatus.CANCELED
        ).filter(
            pk=self.kwargs["pk"], contract_id=self.kwargs["contract_pk"]
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["work_order"] = self.get_work_order()
        return context

    def form_valid(self, form):
        try:
            work_order = cancel_work_order(
                work_order_id=self.kwargs["pk"],
                actor=self.request.user,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Ordem de serviço cancelada com histórico preservado.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=work_order.contract_id,
            pk=work_order.pk,
        )


class WorkOrderAllocationContextMixin(WorkOrderContextMixin):
    def get_work_order(self):
        if not hasattr(self, "work_order"):
            self.work_order = get_object_or_404(
                work_orders_visible_to(self.request.user).filter(
                    contract=self.get_contract()
                ),
                pk=self.kwargs["work_order_pk"],
            )
        return self.work_order

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["work_order"] = self.get_work_order()
        return context


class WorkOrderAllocationCreateView(
    WorkOrderAllocationContextMixin, UserPassesTestMixin, FormView
):
    form_class = WorkOrderAllocationForm
    template_name = "contracts/allocation_form.html"
    raise_exception = True

    def test_func(self):
        return work_orders_writable_by(self.request.user).exclude(
            status=WorkOrderStatus.CANCELED
        ).filter(pk=self.kwargs["work_order_pk"]).exists()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["work_order"] = self.get_work_order()
        return kwargs

    def form_valid(self, form):
        try:
            allocation = create_work_order_allocation(
                work_order_id=self.kwargs["work_order_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Rateio criado com sucesso.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=allocation.work_order.contract_id,
            pk=allocation.work_order_id,
        )


class WorkOrderAllocationUpdateView(WorkOrderAllocationContextMixin, UpdateView):
    model = WorkOrderAllocation
    form_class = WorkOrderAllocationForm
    template_name = "contracts/allocation_form.html"

    def get_queryset(self):
        return allocations_writable_by(self.request.user).exclude(
            status=WorkOrderAllocationStatus.CANCELED
        ).filter(work_order=self.get_work_order())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["work_order"] = self.get_work_order()
        return kwargs

    def form_valid(self, form):
        try:
            allocation = update_work_order_allocation(
                allocation_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Rateio atualizado com sucesso.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=allocation.work_order.contract_id,
            pk=allocation.work_order_id,
        )


class WorkOrderAllocationCancelView(
    WorkOrderAllocationContextMixin, UserPassesTestMixin, FormView
):
    form_class = WorkOrderAllocationCancellationForm
    template_name = "contracts/allocation_cancel.html"
    raise_exception = True

    def get_allocation(self):
        return get_object_or_404(
            allocations_writable_by(self.request.user).exclude(
                status=WorkOrderAllocationStatus.CANCELED
            ).filter(work_order=self.get_work_order()),
            pk=self.kwargs["pk"],
        )

    def test_func(self):
        return allocations_writable_by(self.request.user).exclude(
            status=WorkOrderAllocationStatus.CANCELED
        ).filter(
            pk=self.kwargs["pk"], work_order_id=self.kwargs["work_order_pk"]
        ).exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["allocation"] = self.get_allocation()
        return context

    def form_valid(self, form):
        try:
            allocation = cancel_work_order_allocation(
                allocation_id=self.kwargs["pk"],
                actor=self.request.user,
                reason=form.cleaned_data["reason"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Rateio cancelado com histórico preservado.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=allocation.work_order.contract_id,
            pk=allocation.work_order_id,
        )


class WorkOrderExecutionContextMixin(WorkOrderContextMixin):
    def get_work_order(self):
        if not hasattr(self, "work_order"):
            self.work_order = get_object_or_404(
                work_orders_visible_to(self.request.user).filter(
                    contract=self.get_contract()
                ),
                pk=self.kwargs["work_order_pk"],
            )
        return self.work_order

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["work_order"] = self.get_work_order()
        return context


class WorkOrderExecutionCreateView(
    WorkOrderExecutionContextMixin, UserPassesTestMixin, FormView
):
    form_class = WorkOrderExecutionForm
    template_name = "contracts/execution_form.html"
    raise_exception = True

    def test_func(self):
        return (
            self.request.user.has_perm("contracts.add_workorderexecution")
            and work_orders_writable_by(self.request.user).exclude(
                status=WorkOrderStatus.CANCELED
            ).filter(pk=self.kwargs["work_order_pk"]).exists()
        )

    def form_valid(self, form):
        try:
            execution = create_work_order_execution(
                work_order_id=self.kwargs["work_order_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Execução registrada com sucesso.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=execution.work_order.contract_id,
            pk=execution.work_order_id,
        )


class WorkOrderExecutionUpdateView(WorkOrderExecutionContextMixin, UpdateView):
    model = WorkOrderExecution
    form_class = WorkOrderExecutionForm
    template_name = "contracts/execution_form.html"

    def get_queryset(self):
        return executions_writable_by(self.request.user).exclude(
            work_order__status=WorkOrderStatus.CANCELED
        ).filter(
            work_order=self.get_work_order()
        )

    def form_valid(self, form):
        try:
            execution = update_work_order_execution(
                execution_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Execução atualizada com histórico preservado.")
        return redirect(
            "contracts:work_order_detail",
            contract_pk=execution.work_order.contract_id,
            pk=execution.work_order_id,
        )


class InvoiceContextMixin(WorkOrderExecutionContextMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice_position"] = work_order_invoice_position(self.get_work_order())
        return context


class InvoiceDetailView(InvoiceContextMixin, DetailView):
    model = Invoice
    context_object_name = "invoice"
    template_name = "contracts/invoice_detail.html"

    def get_queryset(self):
        return invoices_visible_to(self.request.user).filter(
            work_order=self.get_work_order()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = (
            self.object.work_order.status != WorkOrderStatus.CANCELED
            and invoices_writable_by(self.request.user).filter(pk=self.object.pk).exists()
        )
        latest_event = self.object.events.first()
        duplicate_ids = latest_event.details.get("possiveis_duplicatas", ()) if latest_event else ()
        context["possible_duplicates"] = invoices_visible_to(self.request.user).filter(
            pk__in=duplicate_ids
        )
        context["check_report"] = invoice_check_report(self.object)
        context["payment_position"] = invoice_payment_position(self.object)
        context["payments"] = payments_visible_to(self.request.user).filter(
            invoice=self.object
        )
        context["can_add_payment"] = (
            self.object.work_order.status != WorkOrderStatus.CANCELED
            and self.request.user.has_perm("contracts.add_payment")
            and invoices_writable_by(self.request.user).filter(pk=self.object.pk).exists()
        )
        context["total_before_invoice"] = (
            context["invoice_position"].invoiced_gross_value.value
            - self.object.gross_value
        )
        return context


class InvoiceCreateView(InvoiceContextMixin, UserPassesTestMixin, FormView):
    form_class = InvoiceForm
    template_name = "contracts/invoice_form.html"
    raise_exception = True

    def test_func(self):
        return (
            self.request.user.has_perm("contracts.add_invoice")
            and work_orders_writable_by(self.request.user).exclude(
                status=WorkOrderStatus.CANCELED
            ).filter(pk=self.kwargs["work_order_pk"]).exists()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["work_order"] = self.get_work_order()
        return kwargs

    def form_valid(self, form):
        try:
            invoice = create_invoice(
                work_order_id=self.kwargs["work_order_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if invoice.possible_duplicate_ids:
            messages.warning(
                self.request,
                "A Nota Fiscal foi registrada com alerta de possível duplicidade; revise os registros indicados.",
            )
        else:
            messages.success(self.request, "Nota Fiscal registrada com sucesso.")
        return redirect(
            "contracts:invoice_detail",
            contract_pk=invoice.contract_id,
            work_order_pk=invoice.work_order_id,
            pk=invoice.pk,
        )


class InvoiceUpdateView(InvoiceContextMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "contracts/invoice_form.html"

    def get_queryset(self):
        return invoices_writable_by(self.request.user).exclude(
            work_order__status=WorkOrderStatus.CANCELED
        ).filter(work_order=self.get_work_order())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["work_order"] = self.get_work_order()
        return kwargs

    def form_valid(self, form):
        try:
            invoice = update_invoice(
                invoice_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        if invoice.possible_duplicate_ids:
            messages.warning(
                self.request,
                "Alteração salva com alerta de possível duplicidade; revise os registros indicados.",
            )
        else:
            messages.success(self.request, "Nota Fiscal atualizada com histórico preservado.")
        return redirect(
            "contracts:invoice_detail",
            contract_pk=invoice.contract_id,
            work_order_pk=invoice.work_order_id,
            pk=invoice.pk,
        )


class PaymentContextMixin(InvoiceContextMixin):
    def get_invoice(self):
        if not hasattr(self, "invoice"):
            self.invoice = get_object_or_404(
                invoices_visible_to(self.request.user).filter(
                    work_order=self.get_work_order()
                ),
                pk=self.kwargs["invoice_pk"],
            )
        return self.invoice

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invoice"] = self.get_invoice()
        context["payment_position"] = invoice_payment_position(self.get_invoice())
        return context


class PaymentDetailView(PaymentContextMixin, DetailView):
    model = Payment
    context_object_name = "payment"
    template_name = "contracts/payment_detail.html"

    def get_queryset(self):
        return payments_visible_to(self.request.user).filter(invoice=self.get_invoice())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_edit"] = (
            self.object.invoice.work_order.status != WorkOrderStatus.CANCELED
            and payments_writable_by(self.request.user).filter(pk=self.object.pk).exists()
        )
        return context


class PaymentCreateView(PaymentContextMixin, UserPassesTestMixin, FormView):
    form_class = PaymentForm
    template_name = "contracts/payment_form.html"
    raise_exception = True

    def test_func(self):
        return (
            self.request.user.has_perm("contracts.add_payment")
            and invoices_writable_by(self.request.user)
            .exclude(work_order__status=WorkOrderStatus.CANCELED)
            .filter(pk=self.kwargs["invoice_pk"])
            .exists()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invoice"] = self.get_invoice()
        return kwargs

    def form_valid(self, form):
        try:
            payment = create_payment(
                invoice_id=self.kwargs["invoice_pk"],
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Pagamento registrado com histórico preservado.")
        return redirect(
            "contracts:payment_detail",
            contract_pk=payment.invoice.contract_id,
            work_order_pk=payment.invoice.work_order_id,
            invoice_pk=payment.invoice_id,
            pk=payment.pk,
        )


class PaymentUpdateView(PaymentContextMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "contracts/payment_form.html"

    def get_queryset(self):
        return payments_writable_by(self.request.user).exclude(
            invoice__work_order__status=WorkOrderStatus.CANCELED
        ).filter(invoice=self.get_invoice())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["invoice"] = self.get_invoice()
        return kwargs

    def form_valid(self, form):
        try:
            payment = update_payment(
                payment_id=self.object.pk,
                actor=self.request.user,
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Pagamento atualizado com histórico preservado.")
        return redirect(
            "contracts:payment_detail",
            contract_pk=payment.invoice.contract_id,
            work_order_pk=payment.invoice.work_order_id,
            invoice_pk=payment.invoice_id,
            pk=payment.pk,
        )


class ExecutiveDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard executivo do contrato (Sprint 37; referência: FiscalSema Light).

    Somente leitura: cada pessoa vê apenas os contratos que já pode ver. O
    Administrador acompanha o sistema, não contratos.
    """

    template_name = "contracts/executive_dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        from accounts.models import UserProfile
        from django.core.exceptions import PermissionDenied

        if request.user.is_authenticated and request.user.profile == UserProfile.ADMINISTRATOR:
            raise PermissionDenied("O Administrador acompanha o sistema, não contratos.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.http import Http404

        context = super().get_context_data(**kwargs)
        contracts = contracts_visible_to(self.request.user).order_by("number", "pk")
        selected = self.request.GET.get("contract")
        if selected:
            if not selected.isdecimal():
                raise Http404("Contrato não encontrado.")
            contract = get_object_or_404(contracts, pk=selected)
        else:
            contract = contracts.first()
        context.update({"contracts": contracts, "contract": contract, "selected_contract": contract})
        if contract is None:
            return context
        today = timezone.localdate()
        dashboard = build_contract_dashboard(contract)
        context.update({
            "dashboard": dashboard,
            "summary": build_executive_summary(contract, dashboard, today=today),
            "evolution": build_monthly_evolution(contract, today=today),
            "validity": build_validity_progress(contract, today=today),
            "can_export": contracts_exportable_by(self.request.user).filter(pk=contract.pk).exists(),
        })
        return context
