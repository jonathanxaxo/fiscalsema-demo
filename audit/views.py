from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from accounts.models import UserProfile
from contracts.services import contracts_with_access_management_visible_to

from .forms import AuditFilterForm
from .services import build_audit_page


class AuditViewBase(LoginRequiredMixin, TemplateView):
    template_name = "audit/audit_list.html"
    contract = None

    def get_filter_form(self):
        return AuditFilterForm(self.request.GET or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        filters = form.cleaned_data if form.is_valid() else {}
        query = self.request.GET.copy()
        query.pop("pagina", None)
        context.update(
            {
                "form": form,
                "contract": self.contract,
                "audit_page": build_audit_page(
                    filters=filters,
                    page_number=self.request.GET.get("pagina"),
                    contract=self.contract,
                    include_global=self.contract is None,
                ),
                "query_without_page": query.urlencode(),
            }
        )
        return context


class GlobalAuditView(UserPassesTestMixin, AuditViewBase):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return (
            user.is_authenticated and user.is_active
            and user.profile == UserProfile.ADMINISTRATOR
            and user.has_perm("accounts.view_authenticationevent")
        )


class ContractAuditView(AuditViewBase):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        self.contract = get_object_or_404(
            contracts_with_access_management_visible_to(request.user),
            pk=kwargs["contract_pk"],
        )
        return super().dispatch(request, *args, **kwargs)
