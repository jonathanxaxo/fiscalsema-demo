from django.contrib import messages
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView, TemplateView, View

from contracts.services import contracts_writable_by

from .forms import ImportMappingForm, ImportUploadForm
from .models import SpreadsheetImport
from .services import (
    build_preview,
    confirm_import,
    contract_for_import,
    create_import,
    record_failed_confirmation,
)


class ContractImportMixin(LoginRequiredMixin):
    contract = None
    spreadsheet_import = None

    def dispatch(self, request, *args, **kwargs):
        if not settings.FILE_FEATURES_ENABLED:
            raise Http404
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.contract = get_object_or_404(
            contracts_writable_by(request.user), pk=kwargs["contract_pk"]
        )
        if "pk" in kwargs:
            self.spreadsheet_import = get_object_or_404(
                SpreadsheetImport.objects.select_related("contract", "created_by"),
                pk=kwargs["pk"], contract=self.contract, created_by=request.user,
            )
            try:
                contract_for_import(request.user, self.contract.pk, self.spreadsheet_import.entity_type)
            except PermissionDenied as exc:
                raise Http404 from exc
        return super().dispatch(request, *args, **kwargs)

    def common_context(self):
        return {"contract": self.contract, "spreadsheet_import": self.spreadsheet_import}


class ImportUploadView(ContractImportMixin, FormView):
    template_name = "data_imports/upload.html"
    form_class = ImportUploadForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.common_context())
        context["imports"] = SpreadsheetImport.objects.filter(
            contract=self.contract, created_by=self.request.user
        )[:20]
        return context

    def form_valid(self, form):
        try:
            contract_for_import(self.request.user, self.contract.pk, form.cleaned_data["entity_type"])
            spreadsheet_import = create_import(
                contract=self.contract,
                actor=self.request.user,
                entity_type=form.cleaned_data["entity_type"],
                uploaded=form.cleaned_data["file"],
            )
        except (PermissionDenied, ValidationError) as exc:
            for message in getattr(exc, "messages", [str(exc)]):
                form.add_error(None, message)
            return self.form_invalid(form)
        return HttpResponseRedirect(reverse(
            "data_imports:mapping", args=[self.contract.pk, spreadsheet_import.pk]
        ))


class ImportMappingView(ContractImportMixin, FormView):
    template_name = "data_imports/mapping.html"
    form_class = ImportMappingForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["spreadsheet_import"] = self.spreadsheet_import
        kwargs["selected_sheet"] = self.request.GET.get("sheet")
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.common_context())
        context["sheet_names"] = self.spreadsheet_import.source_data.keys()
        return context

    def form_valid(self, form):
        try:
            build_preview(
                spreadsheet_import=self.spreadsheet_import,
                actor=self.request.user,
                sheet=form.cleaned_data["sheet"],
                mapping=form.mapping(),
            )
        except (PermissionDenied, ValidationError) as exc:
            for message in getattr(exc, "messages", [str(exc)]):
                form.add_error(None, message)
            return self.form_invalid(form)
        return HttpResponseRedirect(reverse(
            "data_imports:detail", args=[self.contract.pk, self.spreadsheet_import.pk]
        ))


class ImportDetailView(ContractImportMixin, TemplateView):
    template_name = "data_imports/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.common_context())
        return context


class ImportConfirmView(ContractImportMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            confirm_import(spreadsheet_import_id=self.spreadsheet_import.pk, actor=request.user)
        except (PermissionDenied, ValidationError) as exc:
            record_failed_confirmation(
                spreadsheet_import=self.spreadsheet_import, actor=request.user, error=exc
            )
            for message in getattr(exc, "messages", [str(exc)]):
                messages.error(request, message)
        else:
            messages.success(request, "Importação concluída e auditada.")
        return HttpResponseRedirect(reverse(
            "data_imports:detail", args=[self.contract.pk, self.spreadsheet_import.pk]
        ))
