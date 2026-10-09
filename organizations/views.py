from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, ListView, UpdateView

from .forms import OrganizationForm, SectorForm
from .models import Organization, Sector
from .services import create_organization, create_sector, update_organization, update_sector


class OrganizationAdminMixin(LoginRequiredMixin, PermissionRequiredMixin):
    permission_required = "organizations.manage_organizations"
    raise_exception = True


class OrganizationListView(OrganizationAdminMixin, ListView):
    model = Organization
    context_object_name = "organizations"
    template_name = "organizations/organization_list.html"

    def get_queryset(self):
        self.show_inactive = self.request.GET.get("inativos") == "1"
        return super().get_queryset().filter(is_active=not self.show_inactive).prefetch_related("sectors")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_inactive"] = self.show_inactive
        return context


class OrganizationCreateView(OrganizationAdminMixin, FormView):
    form_class = OrganizationForm
    template_name = "organizations/organization_form.html"

    def form_valid(self, form):
        create_organization(
            actor=self.request.user,
            name=form.cleaned_data["name"],
            is_active=form.cleaned_data["is_active"],
        )
        messages.success(self.request, "Organização criada com sucesso.")
        return redirect("organizations:organization_list")


class OrganizationUpdateView(OrganizationAdminMixin, UpdateView):
    model = Organization
    form_class = OrganizationForm
    template_name = "organizations/organization_form.html"

    def form_valid(self, form):
        update_organization(
            organization_id=self.object.pk,
            actor=self.request.user,
            name=form.cleaned_data["name"],
            is_active=form.cleaned_data["is_active"],
        )
        messages.success(self.request, "Organização atualizada com sucesso.")
        return redirect("organizations:organization_list")


class OrganizationStatusView(OrganizationAdminMixin, View):
    def post(self, request, *args, **kwargs):
        organization = get_object_or_404(Organization, pk=kwargs["pk"])
        activate = not organization.is_active
        update_organization(
            organization_id=organization.pk,
            actor=request.user,
            name=organization.name,
            is_active=activate,
        )
        messages.success(
            request,
            "Organização reativada com sucesso."
            if activate
            else "Organização inativada e removida das listas ativas.",
        )
        return redirect("organizations:organization_list")


class SectorListView(OrganizationAdminMixin, ListView):
    model = Sector
    context_object_name = "sectors"
    template_name = "organizations/sector_list.html"

    def get_queryset(self):
        self.show_inactive = self.request.GET.get("inativos") == "1"
        return super().get_queryset().filter(is_active=not self.show_inactive).select_related("organization")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_inactive"] = self.show_inactive
        return context


class SectorCreateView(OrganizationAdminMixin, FormView):
    form_class = SectorForm
    template_name = "organizations/sector_form.html"

    def get_initial(self):
        initial = super().get_initial()
        organization_id = self.request.GET.get("organization")
        if organization_id:
            initial["organization"] = organization_id
        return initial

    def form_valid(self, form):
        create_sector(
            actor=self.request.user,
            organization=form.cleaned_data["organization"],
            name=form.cleaned_data["name"],
            is_active=form.cleaned_data["is_active"],
        )
        messages.success(self.request, "Setor criado com sucesso.")
        return redirect("organizations:sector_list")


class SectorUpdateView(OrganizationAdminMixin, UpdateView):
    model = Sector
    form_class = SectorForm
    template_name = "organizations/sector_form.html"

    def form_valid(self, form):
        update_sector(
            sector_id=self.object.pk,
            actor=self.request.user,
            organization=form.cleaned_data["organization"],
            name=form.cleaned_data["name"],
            is_active=form.cleaned_data["is_active"],
        )
        messages.success(self.request, "Setor atualizado com sucesso.")
        return redirect("organizations:sector_list")


class SectorStatusView(OrganizationAdminMixin, View):
    def post(self, request, *args, **kwargs):
        sector = get_object_or_404(Sector.objects.select_related("organization"), pk=kwargs["pk"])
        activate = not sector.is_active
        try:
            update_sector(
                sector_id=sector.pk,
                actor=request.user,
                organization=sector.organization,
                name=sector.name,
                is_active=activate,
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(
                request,
                "Setor reativado com sucesso."
                if activate
                else "Setor inativado e removido das listas ativas.",
            )
        return redirect("organizations:sector_list")
