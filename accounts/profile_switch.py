"""Troca de perfil Administrador <-> Fiscal (exceção exclusiva da demo).

Somente a conta administrativa que possui um ``ProfileSwitchLink`` pode
alternar. A troca usa a conta Fiscal vinculada, que não possui senha própria;
assim nenhuma regra de permissão existente precisa mudar. Toda troca é
registrada na auditoria de autenticação.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import redirect
from django.views import View

from .models import AccountStatus, AuthenticationEvent, ProfileSwitchLink, UserProfile
from .services import record_authentication_event

SESSION_KEY = "fiscalsema_perfil_admin_origem"
AUTH_BACKEND = settings.AUTHENTICATION_BACKENDS[0]


def _is_active(user):
    return user.is_active and user.status == AccountStatus.ACTIVE


def link_for_administrator(user):
    if not (user.is_authenticated and user.is_superuser and user.profile == UserProfile.ADMINISTRATOR):
        return None
    return ProfileSwitchLink.objects.select_related("fiscal").filter(administrator=user).first()


def link_for_acting_fiscal(request):
    administrator_id = request.session.get(SESSION_KEY)
    if not administrator_id or not request.user.is_authenticated:
        return None
    return (
        ProfileSwitchLink.objects.select_related("administrator")
        .filter(administrator_id=administrator_id, fiscal=request.user)
        .first()
    )


class SwitchToFiscalView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        administrator = request.user
        link = link_for_administrator(administrator)
        if link is None or not _is_active(administrator) or not _is_active(link.fiscal):
            raise PermissionDenied("Troca de perfil não autorizada para esta conta.")
        with transaction.atomic():
            record_authentication_event(
                AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_FISCAL,
                request=request,
                user=administrator,
                details={"conta_fiscal_id": link.fiscal_id},
            )
        login(request, link.fiscal, backend=AUTH_BACKEND)
        request.session[SESSION_KEY] = administrator.pk
        messages.success(request, "Você está atuando como Fiscal.")
        return redirect("home")


class SwitchToAdministratorView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        link = link_for_acting_fiscal(request)
        if link is None or not _is_active(link.administrator):
            raise PermissionDenied("Troca de perfil não autorizada para esta conta.")
        with transaction.atomic():
            record_authentication_event(
                AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_ADMIN,
                request=request,
                user=link.administrator,
                details={"conta_fiscal_id": link.fiscal_id},
            )
        login(request, link.administrator, backend=AUTH_BACKEND)
        request.session.pop(SESSION_KEY, None)
        messages.success(request, "Você voltou ao perfil Administrador.")
        return redirect("home")


def profile_switch(request):
    """Context processor: informa ao layout se a troca está disponível."""
    user = getattr(request, "user", None)
    context = {"can_switch_to_fiscal": False, "acting_as_fiscal": False}
    if user is None or not user.is_authenticated:
        return context
    if request.session.get(SESSION_KEY):
        context["acting_as_fiscal"] = link_for_acting_fiscal(request) is not None
    elif user.is_superuser:
        context["can_switch_to_fiscal"] = link_for_administrator(user) is not None
    return context
