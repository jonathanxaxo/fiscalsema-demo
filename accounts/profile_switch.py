"""Troca de perfil Fiscal <-> Administrador (exceção exclusiva da demo).

Um único ``ProfileSwitchLink`` liga a conta Fiscal usada no dia a dia ao
Administrador da demo. Somente essas duas contas podem alternar entre si; as
demais mantêm o perfil cadastrado. A troca não pede senha da outra conta,
nenhuma regra de permissão existente muda e toda troca é auditada.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import redirect
from django.views import View

from .models import (
    ADMINISTRATOR_PROFILES,
    AccountStatus,
    AuthenticationEvent,
    ProfileSwitchLink,
)
from .services import record_authentication_event

SESSION_KEY = "fiscalsema_perfil_conta_origem"
AUTH_BACKEND = settings.AUTHENTICATION_BACKENDS[0]


def _is_active(user):
    return user.is_active and user.status == AccountStatus.ACTIVE


def _profile_label(user):
    return "Administrador Geral" if user.profile in ADMINISTRATOR_PROFILES else "Fiscal Titular"


def _other_account(link, user):
    return link.fiscal if link.administrator_id == user.pk else link.administrator


def link_for_user(user):
    if not user.is_authenticated:
        return None
    return (
        ProfileSwitchLink.objects.select_related("administrator", "fiscal")
        .filter(Q(administrator=user) | Q(fiscal=user))
        .first()
    )


def _acting_link(request):
    """Vínculo válido quando a sessão está atuando no outro perfil."""
    origin_id = request.session.get(SESSION_KEY)
    if not origin_id:
        return None
    link = link_for_user(request.user)
    if link is None or origin_id not in {link.administrator_id, link.fiscal_id}:
        return None
    if origin_id == request.user.pk:
        return None
    return link


class SwitchProfileView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        current = request.user
        acting_link = _acting_link(request)
        if acting_link is not None:
            target = _other_account(acting_link, current)
            origin = target
        else:
            if request.session.get(SESSION_KEY):
                raise PermissionDenied("Troca de perfil não autorizada para esta sessão.")
            link = link_for_user(current)
            if link is None:
                raise PermissionDenied("Troca de perfil não autorizada para esta conta.")
            target = _other_account(link, current)
            origin = current

        if not _is_active(current) or not _is_active(target):
            raise PermissionDenied("Troca de perfil não autorizada: conta inativa.")

        event_type = (
            AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_ADMIN
            if target.profile in ADMINISTRATOR_PROFILES
            else AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_FISCAL
        )
        record_authentication_event(
            event_type,
            request=request,
            user=origin,
            details={"conta_atual_id": current.pk, "conta_destino_id": target.pk},
        )
        login(request, target, backend=AUTH_BACKEND)
        if target.pk != origin.pk:
            request.session[SESSION_KEY] = origin.pk
        else:
            request.session.pop(SESSION_KEY, None)
        messages.success(request, f"Você está atuando como {_profile_label(target)}.")
        return redirect("home")


def profile_switch(request):
    """Context processor: rótulos da troca de perfil para o layout."""
    context = {"profile_switch_target": "", "acting_as": "", "acting_return": ""}
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return context
    if request.session.get(SESSION_KEY):
        link = _acting_link(request)
        if link is not None:
            context["acting_as"] = _profile_label(user)
            context["acting_return"] = _profile_label(_other_account(link, user))
        return context
    link = link_for_user(user)
    if link is not None:
        context["profile_switch_target"] = _profile_label(_other_account(link, user))
    return context
