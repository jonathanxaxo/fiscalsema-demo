import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect
from django.views.generic import DetailView, ListView, View

from .drafts import (
    confirm_assistant_draft, confirm_assistant_draft_batch, reject_assistant_draft,
)
from .models import AssistantDraft


class DraftOwnerMixin(LoginRequiredMixin):
    def get_queryset(self):
        return AssistantDraft.objects.select_related(
            "contract", "requested_by", "created_by_credential", "reviewed_by"
        ).filter(requested_by=self.request.user)


class AssistantDraftListView(DraftOwnerMixin, ListView):
    template_name = "api_v1/draft_list.html"
    context_object_name = "drafts"
    paginate_by = 25


class AssistantDraftDetailView(DraftOwnerMixin, DetailView):
    template_name = "api_v1/draft_detail.html"
    context_object_name = "draft"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payload_json"] = json.dumps(self.object.payload, ensure_ascii=False, indent=2)
        context["evidence_json"] = json.dumps(self.object.evidence, ensure_ascii=False, indent=2)
        context["comparison_json"] = json.dumps(self.object.comparison, ensure_ascii=False, indent=2)
        context["consistency_json"] = json.dumps(
            self.object.consistency_result, ensure_ascii=False, indent=2,
        )
        return context


class AssistantDraftConfirmView(DraftOwnerMixin, View):
    def post(self, request, pk):
        if not self.get_queryset().filter(pk=pk).exists():
            raise Http404
        try:
            draft, target = confirm_assistant_draft(draft_id=pk, actor=request.user)
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, f"Confirmação recusada: {exc}")
            return redirect("assistant_drafts:detail", pk=pk)
        messages.success(
            request,
            f"Rascunho confirmado. Registro {target._meta.verbose_name} #{target.pk} gravado.",
        )
        return redirect("assistant_drafts:detail", pk=draft.pk)


class AssistantDraftRejectView(DraftOwnerMixin, View):
    def post(self, request, pk):
        if not self.get_queryset().filter(pk=pk).exists():
            raise Http404
        try:
            reject_assistant_draft(
                draft_id=pk, actor=request.user, reason=request.POST.get("reason", ""),
            )
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, f"Rejeição não registrada: {exc}")
        else:
            messages.success(request, "Rascunho rejeitado e preservado na auditoria.")
        return redirect("assistant_drafts:detail", pk=pk)


class AssistantDraftBatchConfirmView(DraftOwnerMixin, View):
    def post(self, request, batch_id):
        if not self.get_queryset().filter(batch_id=batch_id).exists():
            raise Http404
        try:
            results = confirm_assistant_draft_batch(batch_id=batch_id, actor=request.user)
        except (ValidationError, PermissionDenied) as exc:
            messages.error(request, f"Confirmação do lote recusada: {exc}")
        else:
            messages.success(
                request,
                f"Lote confirmado integralmente: {len(results)} registro(s) gravado(s).",
            )
        return redirect("assistant_drafts:list")
