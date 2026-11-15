"""Telas do catálogo de serviços e da memória de cálculo da OS (Sprint 38).

Referência: FiscalSema Light (somente lido), adaptado ao Demo.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from .forms import (
    InvoiceReturnForm,
    ServiceCatalogEntryForm,
    ServiceLineActionForm,
    WorkOrderServiceLineForm,
)
from .models import ServiceLineStatus, WorkOrderServiceLine, WorkOrderStatus
from .service_catalog import (
    accept_service_line,
    add_work_order_service_line,
    create_service_catalog_entry,
    homologate_accepted_service_lines,
    homologate_service_line,
    register_service_line_delivery,
    reject_service_line,
    remove_work_order_service_line,
    update_service_catalog_entry,
    update_work_order_service_line,
)
from .services import (
    contract_is_read_only_for,
    contracts_visible_to,
    contracts_writable_by,
    invoices_writable_by,
    return_invoice,
    work_orders_writable_by,
)


class CatalogContractMixin(LoginRequiredMixin):
    def get_contract(self):
        if not hasattr(self, "contract"):
            self.contract = get_object_or_404(
                contracts_visible_to(self.request.user),
                pk=self.kwargs["contract_pk"],
            )
        return self.contract

    def can_edit_catalog(self):
        return self.request.user.has_perm("contracts.change_contract") and contracts_writable_by(
            self.request.user
        ).filter(pk=self.get_contract().pk).exists()


class ServiceCatalogListView(CatalogContractMixin, ListView):
    template_name = "contracts/service_catalog_list.html"
    context_object_name = "entries"

    def get_queryset(self):
        return self.get_contract().service_catalog.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.get_contract()
        context["can_edit"] = self.can_edit_catalog()
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.get_contract()
        )
        return context


class ServiceCatalogFormView(CatalogContractMixin, View):
    template_name = "contracts/service_catalog_form.html"

    def get_entry(self):
        if "pk" not in self.kwargs:
            return None
        return get_object_or_404(self.get_contract().service_catalog, pk=self.kwargs["pk"])

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.can_edit_catalog():
            raise PermissionDenied("Somente o fiscal do contrato altera o catálogo.")
        return super().dispatch(request, *args, **kwargs)

    def render_form(self, form, entry):
        return render(
            self.request,
            self.template_name,
            {"form": form, "contract": self.get_contract(), "entry": entry},
        )

    def get(self, request, *args, **kwargs):
        entry = self.get_entry()
        return self.render_form(ServiceCatalogEntryForm(instance=entry), entry)

    def post(self, request, *args, **kwargs):
        entry = self.get_entry()
        form = ServiceCatalogEntryForm(request.POST, instance=entry)
        if not form.is_valid():
            return self.render_form(form, entry)
        data = {field: form.cleaned_data[field] for field in form.fields}
        try:
            if entry is None:
                create_service_catalog_entry(
                    contract_id=self.get_contract().pk, actor=request.user, **data
                )
                messages.success(request, "Serviço cadastrado no catálogo do contrato.")
            else:
                update_service_catalog_entry(entry_id=entry.pk, actor=request.user, **data)
                messages.success(request, "Serviço do catálogo atualizado.")
        except ValidationError as error:
            form.add_error(None, error)
            return self.render_form(form, entry)
        return redirect("contracts:service_catalog", contract_pk=self.get_contract().pk)


class WorkOrderServiceLineMixin(CatalogContractMixin, View):
    template_name = "contracts/work_order_service_line_form.html"

    def get_work_order(self):
        if not hasattr(self, "work_order"):
            self.work_order = get_object_or_404(
                work_orders_writable_by(self.request.user).filter(
                    contract=self.get_contract()
                ),
                pk=self.kwargs["work_order_pk"],
            )
            if self.work_order.status == WorkOrderStatus.CANCELED:
                raise PermissionDenied("OS cancelada é somente leitura.")
        return self.work_order

    def get_line(self):
        if "pk" not in self.kwargs:
            return None
        return get_object_or_404(
            WorkOrderServiceLine.objects.select_related("catalog_entry"),
            pk=self.kwargs["pk"],
            work_order=self.get_work_order(),
        )

    def detail_redirect(self):
        return redirect(
            "contracts:work_order_detail",
            contract_pk=self.get_contract().pk,
            pk=self.get_work_order().pk,
        )

    def render_form(self, form, line):
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "contract": self.get_contract(),
                "work_order": self.get_work_order(),
                "line": line,
            },
        )


class WorkOrderServiceLineFormView(WorkOrderServiceLineMixin):
    def get(self, request, *args, **kwargs):
        line = self.get_line()
        form = WorkOrderServiceLineForm(contract=self.get_contract(), line=line)
        return self.render_form(form, line)

    def post(self, request, *args, **kwargs):
        line = self.get_line()
        form = WorkOrderServiceLineForm(request.POST, contract=self.get_contract(), line=line)
        if not form.is_valid():
            return self.render_form(form, line)
        try:
            if line is None:
                add_work_order_service_line(
                    work_order_id=self.get_work_order().pk,
                    actor=request.user,
                    catalog_entry=form.cleaned_data["catalog_entry"],
                    complexity=form.cleaned_data["complexity"],
                    quantity=form.cleaned_data["quantity"],
                )
                messages.success(request, "Serviço incluído na memória de cálculo da OS.")
            else:
                update_work_order_service_line(
                    line_id=line.pk,
                    actor=request.user,
                    complexity=form.cleaned_data["complexity"],
                    quantity=form.cleaned_data["quantity"],
                )
                messages.success(request, "Serviço da OS atualizado.")
        except ValidationError as error:
            form.add_error(None, error)
            return self.render_form(form, line)
        return self.detail_redirect()


class WorkOrderServiceLineRemoveView(WorkOrderServiceLineMixin):
    template_name = "contracts/work_order_service_line_remove.html"

    def get(self, request, *args, **kwargs):
        line = self.get_line()
        if line is None:
            raise Http404
        return render(
            request,
            self.template_name,
            {"contract": self.get_contract(), "work_order": self.get_work_order(), "line": line},
        )

    def post(self, request, *args, **kwargs):
        line = self.get_line()
        if line is None:
            raise Http404
        try:
            remove_work_order_service_line(line_id=line.pk, actor=request.user)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return self.detail_redirect()
        messages.success(request, "Serviço removido da memória de cálculo da OS.")
        return self.detail_redirect()


LINE_ACTION_STATUS = {
    "entregar": ServiceLineStatus.IN_PROGRESS,
    "aceitar": ServiceLineStatus.DELIVERED,
    "recusar": ServiceLineStatus.DELIVERED,
    "homologar": ServiceLineStatus.ACCEPTED,
}

LINE_ACTION_MESSAGES = {
    "entregar": "Entrega do serviço registrada. Confira e registre o aceite ou a recusa.",
    "aceitar": "Serviço aceito. Falta assinar o Termo de Homologação para liberar o faturamento.",
    "recusar": "Serviço recusado e devolvido para ajuste da fábrica.",
    "homologar": "Serviço homologado e liberado para faturamento.",
}


class WorkOrderServiceLineActionView(WorkOrderServiceLineMixin):
    """Entrega, aceite, recusa e homologação de um serviço da OS."""

    template_name = "contracts/work_order_service_line_action.html"

    def get_action(self):
        action = self.kwargs["action"]
        if action not in LINE_ACTION_STATUS:
            raise Http404
        return action

    def render_action(self, form, line):
        title = ServiceLineActionForm.ACTIONS[form.action][0]
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "contract": self.get_contract(),
                "work_order": self.get_work_order(),
                "line": line,
                "lines": (line,),
                "title": title,
            },
        )

    def get(self, request, *args, **kwargs):
        action = self.get_action()
        line = self.get_line()
        if line.delivery_status != LINE_ACTION_STATUS[action]:
            messages.error(request, "Esta ação não vale para a situação atual do serviço.")
            return self.detail_redirect()
        return self.render_action(ServiceLineActionForm(action=action), line)

    def post(self, request, *args, **kwargs):
        action = self.get_action()
        line = self.get_line()
        form = ServiceLineActionForm(request.POST, action=action)
        if not form.is_valid():
            return self.render_action(form, line)
        date = form.cleaned_data["event_date"]
        try:
            if action == "entregar":
                register_service_line_delivery(line_id=line.pk, actor=request.user, delivered_at=date)
            elif action == "aceitar":
                accept_service_line(line_id=line.pk, actor=request.user, accepted_at=date)
            elif action == "recusar":
                reject_service_line(
                    line_id=line.pk,
                    actor=request.user,
                    rejected_at=date,
                    reason=form.cleaned_data["reason"],
                )
            else:
                homologate_service_line(
                    line_id=line.pk,
                    actor=request.user,
                    homologated_at=date,
                    reference=form.cleaned_data["reference"],
                )
        except ValidationError as error:
            _add_service_error(form, error)
            return self.render_action(form, line)
        messages.success(request, LINE_ACTION_MESSAGES[action])
        return self.detail_redirect()


class WorkOrderHomologateAcceptedView(WorkOrderServiceLineMixin):
    """Homologa de uma vez todos os serviços aceitos da OS, com um único termo."""

    template_name = "contracts/work_order_service_line_action.html"

    def accepted_lines(self):
        return tuple(
            self.get_work_order().service_lines.filter(
                delivery_status=ServiceLineStatus.ACCEPTED
            ).order_by("pk")
        )

    def render_action(self, form, lines):
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "contract": self.get_contract(),
                "work_order": self.get_work_order(),
                "lines": lines,
                "title": "Homologar todos os serviços aceitos",
            },
        )

    def get(self, request, *args, **kwargs):
        lines = self.accepted_lines()
        if not lines:
            messages.error(request, "Não há serviços aceitos aguardando homologação.")
            return self.detail_redirect()
        return self.render_action(ServiceLineActionForm(action="homologar"), lines)

    def post(self, request, *args, **kwargs):
        lines = self.accepted_lines()
        form = ServiceLineActionForm(request.POST, action="homologar")
        if not form.is_valid():
            return self.render_action(form, lines)
        try:
            homologated = homologate_accepted_service_lines(
                work_order_id=self.get_work_order().pk,
                actor=request.user,
                homologated_at=form.cleaned_data["event_date"],
                reference=form.cleaned_data["reference"],
            )
        except ValidationError as error:
            _add_service_error(form, error)
            return self.render_action(form, lines)
        messages.success(
            request, f"{len(homologated)} serviço(s) homologado(s) e liberado(s) para faturamento."
        )
        return self.detail_redirect()


class InvoiceReturnView(WorkOrderServiceLineMixin):
    """Sprint 39: devolve a NF para correção; a NF corrigida a substitui."""

    template_name = "contracts/invoice_return.html"

    def get_invoice(self):
        return get_object_or_404(
            invoices_writable_by(self.request.user).filter(returned_at__isnull=True),
            pk=self.kwargs["pk"], work_order=self.get_work_order(),
        )

    def render_return(self, form, invoice):
        return render(self.request, self.template_name, {
            "form": form, "contract": self.get_contract(), "work_order": self.get_work_order(), "invoice": invoice,
        })

    def get(self, request, *args, **kwargs):
        return self.render_return(InvoiceReturnForm(), self.get_invoice())

    def post(self, request, *args, **kwargs):
        invoice = self.get_invoice()
        form = InvoiceReturnForm(request.POST)
        if not form.is_valid():
            return self.render_return(form, invoice)
        try:
            return_invoice(invoice_id=invoice.pk, actor=request.user,
                           returned_at=form.cleaned_data["returned_at"], reason=form.cleaned_data["reason"])
        except ValidationError as error:
            _add_service_error(form, error)
            return self.render_return(form, invoice)
        messages.success(request, "NF devolvida para correção. Ela saiu dos cálculos; cadastre a NF corrigida "
                                  "indicando que substitui esta.")
        return redirect("contracts:invoice_detail", contract_pk=self.get_contract().pk,
                        work_order_pk=self.get_work_order().pk, pk=invoice.pk)


def _add_service_error(form, error):
    """Mostra o erro do serviço no campo do formulário quando houver correspondência."""
    field_map = {
        "delivered_at": "event_date",
        "accepted_at": "event_date",
        "rejected_at": "event_date",
        "homologated_at": "event_date",
    }
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            target = field_map.get(field, field)
            if target not in form.fields:
                target = None
            for item in errors:
                form.add_error(target, item)
    else:
        form.add_error(None, error)
