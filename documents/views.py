from django.contrib import messages
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import DetailView, FormView

from contracts.services import (
    contract_is_read_only_for,
    contracts_visible_to,
    contracts_writable_by,
)

from .forms import DocumentUploadForm
from .models import DocumentEvent
from .services import (
    can_open_document_content,
    create_document,
    document_metadata_visible_to,
    documents_visible_to,
)


class ContractDocumentContextMixin(LoginRequiredMixin):
    contract = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.contract = get_object_or_404(
            contracts_visible_to(request.user), pk=kwargs["contract_pk"]
        )
        return super().dispatch(request, *args, **kwargs)


class DocumentListView(ContractDocumentContextMixin, DetailView):
    template_name = "documents/document_list.html"
    context_object_name = "contract"

    def get_object(self, queryset=None):
        return self.contract

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["documents"] = document_metadata_visible_to(self.request.user).filter(
            contract=self.contract
        )
        context["can_open_documents"] = can_open_document_content(self.request.user)
        context["can_upload"] = (
            settings.FILE_FEATURES_ENABLED
            and contracts_writable_by(self.request.user).filter(pk=self.contract.pk).exists()
            and self.request.user.has_perm("documents.add_document")
        )
        context["is_read_only_access"] = contract_is_read_only_for(
            self.request.user, self.contract
        )
        return context


class DocumentUploadView(ContractDocumentContextMixin, UserPassesTestMixin, FormView):
    template_name = "documents/document_form.html"
    form_class = DocumentUploadForm
    raise_exception = True

    def test_func(self):
        return (
            settings.FILE_FEATURES_ENABLED
            and contracts_writable_by(self.request.user).filter(pk=self.contract.pk).exists()
            and self.request.user.has_perm("documents.add_document")
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["contract"] = self.contract
        return kwargs

    def form_valid(self, form):
        try:
            create_document(
                contract_id=self.contract.pk,
                actor=self.request.user,
                file=form.cleaned_data.pop("file"),
                **form.cleaned_data,
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "Documento anexado com integridade registrada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("documents:list", args=[self.contract.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contract"] = self.contract
        return context


class DocumentDownloadView(LoginRequiredMixin, DetailView):
    http_method_names = ["get", "head", "options"]

    def get(self, request, *args, **kwargs):
        if not settings.FILE_FEATURES_ENABLED:
            raise Http404
        document = get_object_or_404(documents_visible_to(request.user), pk=kwargs["pk"])
        storage_name = document.file.name.replace("\\", "/")
        if storage_name.startswith("/") or ".." in storage_name.split("/"):
            raise Http404
        try:
            document.file.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404
        DocumentEvent.objects.create(
            event_type=DocumentEvent.EventType.DOWNLOADED,
            document=document,
            contract=document.contract,
            actor=request.user,
            details={"documento_id": document.pk, "sha256": document.sha256},
        )
        response = FileResponse(
            document.file,
            as_attachment=True,
            filename=document.original_name,
            content_type=document.mime_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
