from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, TemplateView

from .forms import (
    AccountPasswordChangeForm,
    AccountSetPasswordForm,
    AdministrativeFiscalCreationForm,
    EmailAuthenticationForm,
    FiscalRegistrationForm,
    RegistrationReviewForm,
    UserProfileChangeForm,
    UserOrganizationAssignmentForm,
)
from .models import AuthenticationEvent, RegistrationRequest, RegistrationStatus, User
from organizations.services import assign_user_organization
from .services import (
    archive_user,
    archive_registration_request,
    change_user_profile,
    change_user_status,
    clear_login_failures,
    record_authentication_event,
    review_registration_request,
    restore_user,
)


class AccountLoginView(LoginView):
    authentication_form = EmailAuthenticationForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        clear_login_failures(form.get_user().email)
        record_authentication_event(
            AuthenticationEvent.EventType.LOGIN_SUCCESS,
            request=self.request,
            user=form.get_user(),
            email=form.get_user().email,
        )
        return response


class AccountLogoutView(LogoutView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        user = request.user if request.user.is_authenticated else None
        response = super().post(request, *args, **kwargs)
        if user:
            record_authentication_event(
                AuthenticationEvent.EventType.LOGOUT,
                request=request,
                user=user,
                email=user.email,
            )
        return response


class AccountPasswordChangeView(PasswordChangeView):
    form_class = AccountPasswordChangeForm
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:password_change_done")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=("must_change_password",))
            update_session_auth_hash(self.request, user)
        record_authentication_event(
            AuthenticationEvent.EventType.PASSWORD_CHANGED,
            request=self.request,
            user=user,
            email=user.email,
            details={"origem": "troca_autenticada"},
        )
        return response


class AccountPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    form_class = AccountSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        user = form.user
        response = super().form_valid(form)
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=("must_change_password",))
        record_authentication_event(
            AuthenticationEvent.EventType.PASSWORD_CHANGED,
            request=self.request,
            user=user,
            email=user.email,
            details={"origem": "recuperacao"},
        )
        return response


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class FiscalRegistrationView(FormView):
    form_class = FiscalRegistrationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:registration_submitted")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "Já existe uma conta com este e-mail.")
            return self.form_invalid(form)
        record_authentication_event(
            AuthenticationEvent.EventType.REGISTRATION_REQUESTED,
            request=self.request,
            user=user,
            email=user.email,
            details={
                "solicitacao_id": user.registration_request.pk,
                "perfil_solicitado": user.profile,
            },
        )
        return super().form_valid(form)


class RegistrationSubmittedView(TemplateView):
    template_name = "accounts/registration_submitted.html"


class AdministrativeAccessMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True


class RegistrationRequestListView(AdministrativeAccessMixin, ListView):
    permission_required = "accounts.review_registration"
    model = RegistrationRequest
    context_object_name = "registration_requests"
    template_name = "accounts/admin/registration_list.html"

    def get_queryset(self):
        queryset = super().get_queryset().select_related("user", "reviewed_by")
        self.show_archived = self.request.GET.get("arquivadas") == "1"
        queryset = queryset.filter(archived_at__isnull=not self.show_archived)
        selected_status = self.request.GET.get("status", RegistrationStatus.PENDING)
        valid_statuses = {value for value, _label in RegistrationStatus.choices}
        if selected_status in valid_statuses:
            queryset = queryset.filter(status=selected_status)
        self.selected_status = selected_status if selected_status in valid_statuses else ""
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.selected_status
        context["status_choices"] = RegistrationStatus.choices
        context["show_archived"] = self.show_archived
        return context


class RegistrationRequestArchiveView(AdministrativeAccessMixin, View):
    permission_required = "accounts.review_registration"

    def post(self, request, *args, **kwargs):
        try:
            archive_registration_request(registration_id=kwargs["pk"], actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, "Solicitação arquivada sem apagar o histórico.")
        return redirect("accounts_admin:registration_list")


class RegistrationRequestReviewView(AdministrativeAccessMixin, FormView):
    permission_required = "accounts.review_registration"
    form_class = RegistrationReviewForm
    template_name = "accounts/admin/registration_review.html"

    def get_registration_request(self):
        if not hasattr(self, "registration_request"):
            self.registration_request = get_object_or_404(
                RegistrationRequest.objects.select_related("user", "reviewed_by"),
                pk=self.kwargs["pk"],
            )
        return self.registration_request

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["registration_request"] = self.get_registration_request()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["requested_profile"] = self.get_registration_request().requested_profile
        return kwargs

    def form_valid(self, form):
        try:
            registration = review_registration_request(
                self.get_registration_request().pk,
                self.request.user,
                form.cleaned_data["action"],
                form.cleaned_data.get("rejection_reason", ""),
                form.cleaned_data.get("organization").pk
                if form.cleaned_data.get("organization")
                else None,
                form.cleaned_data.get("sector").pk
                if form.cleaned_data.get("sector")
                else None,
                form.cleaned_data.get("approved_profile"),
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        action_label = "aprovada" if registration.status == RegistrationStatus.APPROVED else "rejeitada"
        messages.success(self.request, f"Solicitação {action_label} com sucesso.")
        return redirect("accounts_admin:registration_list")


class AdministrativeFiscalCreateView(AdministrativeAccessMixin, FormView):
    permission_required = "accounts.manage_users"
    form_class = AdministrativeFiscalCreationForm
    template_name = "accounts/admin/fiscal_create.html"

    def form_valid(self, form):
        try:
            user = form.save()
        except IntegrityError:
            form.add_error("email", "Já existe uma conta com este e-mail.")
            return self.form_invalid(form)
        record_authentication_event(
            AuthenticationEvent.EventType.USER_CREATED,
            request=self.request,
            user=user,
            email=user.email,
            details={"autor_id": self.request.user.pk, "perfil": user.profile},
        )
        messages.success(
            self.request,
            "Usuário criado com sucesso. A troca da senha temporária será exigida no primeiro acesso.",
        )
        return redirect(reverse("accounts_admin:fiscal_create"))


class AdministrativeUserListView(AdministrativeAccessMixin, ListView):
    permission_required = ("accounts.manage_users", "organizations.manage_organizations")
    model = User
    context_object_name = "users"
    template_name = "accounts/admin/user_list.html"

    def get_queryset(self):
        self.show_archived = self.request.GET.get("excluidos") == "1"
        return (
            super().get_queryset()
            .select_related("organization", "sector", "archived_by")
            .filter(archived_at__isnull=not self.show_archived)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_archived"] = self.show_archived
        return context


class AdministrativeUserStatusView(AdministrativeAccessMixin, View):
    permission_required = "accounts.manage_users"

    def post(self, request, *args, **kwargs):
        try:
            user = change_user_status(
                user_id=kwargs["pk"], actor=request.user, action=kwargs["action"]
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, f"Status de {user.full_name} atualizado com segurança.")
        return redirect("accounts_admin:user_list")


class AdministrativeUserProfileView(AdministrativeAccessMixin, FormView):
    permission_required = "accounts.manage_users"
    form_class = UserProfileChangeForm
    template_name = "accounts/admin/user_profile.html"

    def get_target(self):
        if not hasattr(self, "target_user"):
            self.target_user = get_object_or_404(User, pk=self.kwargs["pk"])
        return self.target_user

    def form_valid(self, form):
        try:
            target = change_user_profile(
                user_id=self.get_target().pk,
                actor=self.request.user,
                profile=form.cleaned_data["profile"],
            )
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(
            self.request,
            f"Perfil de {target.full_name} alterado com auditoria e sessões encerradas.",
        )
        return redirect("accounts_admin:user_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.get_target()
        return context


class AdministrativeUserArchiveView(AdministrativeAccessMixin, View):
    permission_required = "accounts.manage_users"

    def post(self, request, *args, **kwargs):
        try:
            archive_user(user_id=kwargs["pk"], actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(
                request,
                "Conta excluída logicamente. O acesso foi bloqueado e o histórico preservado.",
            )
        return redirect("accounts_admin:user_list")


class AdministrativeUserRestoreView(AdministrativeAccessMixin, View):
    permission_required = "accounts.manage_users"

    def post(self, request, *args, **kwargs):
        try:
            restore_user(user_id=kwargs["pk"], actor=request.user)
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, "Conta restaurada como inativa. Ative-a somente se necessário.")
        return redirect(f"{reverse('accounts_admin:user_list')}?excluidos=1")


class UserOrganizationAssignmentView(AdministrativeAccessMixin, FormView):
    permission_required = ("accounts.manage_users", "organizations.manage_organizations")
    form_class = UserOrganizationAssignmentForm
    template_name = "accounts/admin/user_organization_form.html"

    def get_target_user(self):
        if not hasattr(self, "target_user"):
            self.target_user = get_object_or_404(
                User.objects.select_related("organization", "sector"),
                pk=self.kwargs["pk"],
            )
        return self.target_user

    def get_initial(self):
        user = self.get_target_user()
        return {"organization": user.organization_id, "sector": user.sector_id}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["target_user"] = self.get_target_user()
        return context

    def form_valid(self, form):
        assign_user_organization(
            user_id=self.get_target_user().pk,
            actor=self.request.user,
            organization_id=form.cleaned_data["organization"].pk,
            sector_id=form.cleaned_data["sector"].pk if form.cleaned_data["sector"] else None,
        )
        messages.success(self.request, "Vínculo institucional atualizado com sucesso.")
        return redirect("accounts_admin:user_list")


class SessionKeepAliveView(View):
    """Sprint 49: o navegador avisa que a pessoa está usando a tela (digitando, rolando)
    sem enviar formulário. Só atualiza a hora da última atividade; não altera nenhum dado."""

    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse, JsonResponse

        if not request.user.is_authenticated:
            return JsonResponse({"erro": "Sessão encerrada. Entre novamente."}, status=401)
        response = HttpResponse(status=204)
        response["Cache-Control"] = "no-store"
        return response


class SessionTabClosedView(View):
    """Sprint 52: o sistema foi fechado (nenhuma aba dele estava aberta) e reaberto.

    O navegador avisa por aqui; a sessão é encerrada, a saída vai para a auditoria e a
    pessoa entra de novo com a senha. Só aceita POST com proteção CSRF.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import logout
        from django.http import JsonResponse

        user = request.user if request.user.is_authenticated else None
        if user:
            record_authentication_event(
                AuthenticationEvent.EventType.LOGOUT, request=request, user=user, email=user.email,
                details={"motivo": "sistema fechado e reaberto"},
            )
            logout(request)
            messages.info(request, "Por segurança, o sistema foi fechado. Entre novamente com a sua senha.")
        return JsonResponse({"ok": True, "login": reverse("accounts:login")})
