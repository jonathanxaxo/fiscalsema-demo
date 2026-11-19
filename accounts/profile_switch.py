"""Troca de perfil exclusiva da demonstração, com identidade real por perfil.

Uma única conta controladora entra com a própria senha. A sessão pode passar a
usar contas-alvo previamente vinculadas, inclusive contas internas com senha
inutilizável. Assim as permissões continuam sendo as permissões reais do
backend e nenhuma conta comum ganha o direito de alternar perfis.
"""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views import View

from .models import (
    ADMINISTRATOR_PROFILES,
    FISCAL_TITULAR_PROFILES,
    AccountStatus,
    AuthenticationEvent,
    DemoProfileSwitch,
    UserProfile,
)
from .services import record_authentication_event

SESSION_KEY = "fiscalsema_perfil_conta_origem"
AUTH_BACKEND = settings.AUTHENTICATION_BACKENDS[0]


def _is_active(user):
    return (
        user.is_active
        and user.status == AccountStatus.ACTIVE
        and user.archived_at is None
    )


def _profile_label(user):
    return user.get_profile_display()


def _switch_queryset():
    return DemoProfileSwitch.objects.select_related("controller").prefetch_related(
        "targets__user"
    )


def _switch_for_request(request):
    """Retorna o vínculo somente para a controladora ou sua sessão delegada."""
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    origin_id = request.session.get(SESSION_KEY)
    if origin_id:
        if origin_id == user.pk:
            return None
        switch = _switch_queryset().filter(controller_id=origin_id).first()
        if switch is None:
            return None
        if not any(target.user_id == user.pk for target in switch.targets.all()):
            return None
        return switch
    return _switch_queryset().filter(controller=user).first()


def _active_targets(switch):
    return [
        target
        for target in switch.targets.all()
        if _is_active(target.user)
        and (not target.is_internal or not target.user.has_usable_password())
        and target.user.profile == target.profile
    ]


def _legacy_event_type(targets, target):
    profiles = {item.profile for item in targets}
    legacy_pair = profiles <= {
        UserProfile.ADMINISTRATOR_GENERAL,
        UserProfile.FISCAL_TITULAR,
    }
    if not legacy_pair:
        return AuthenticationEvent.EventType.PROFILE_SWITCHED
    if target.profile in ADMINISTRATOR_PROFILES:
        return AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_ADMIN
    if target.profile in FISCAL_TITULAR_PROFILES:
        return AuthenticationEvent.EventType.PROFILE_SWITCHED_TO_FISCAL
    return AuthenticationEvent.EventType.PROFILE_SWITCHED


class SwitchProfileView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        switch = _switch_for_request(request)
        if switch is None:
            raise PermissionDenied("Troca de perfil não autorizada para esta conta ou sessão.")

        current = request.user
        origin = switch.controller
        targets = _active_targets(switch)
        if not _is_active(origin) or not any(item.user_id == current.pk for item in targets):
            raise PermissionDenied("Troca de perfil não autorizada: conta inativa ou vínculo inválido.")

        requested_profile = (request.POST.get("profile") or "").strip()
        candidates = [item for item in targets if item.user_id != current.pk]
        if requested_profile:
            candidates = [item for item in candidates if item.profile == requested_profile]
        elif len(candidates) != 1:
            raise PermissionDenied("Selecione o perfil de demonstração desejado.")
        if len(candidates) != 1:
            raise PermissionDenied("Perfil de demonstração não autorizado.")

        target = candidates[0].user
        record_authentication_event(
            _legacy_event_type(targets, target),
            request=request,
            user=origin,
            details={
                "conta_atual_id": current.pk,
                "conta_destino_id": target.pk,
                "perfil_origem": current.profile,
                "perfil_destino": target.profile,
            },
        )
        login(request, target, backend=AUTH_BACKEND)
        if target.pk != origin.pk:
            request.session[SESSION_KEY] = origin.pk
        else:
            request.session.pop(SESSION_KEY, None)
        messages.success(request, f"Você está atuando como {_profile_label(target)}.")
        return redirect("home")


def profile_switch(request):
    """Context processor do seletor, sem conceder autorização pela interface."""
    context = {
        "profile_switch_target": "",
        "profile_switch_options": (),
        "profile_switch_origin_profile": "",
        "acting_as": "",
        "acting_return": "",
    }
    switch = _switch_for_request(request)
    if switch is None:
        return context

    user = request.user
    targets = _active_targets(switch)
    if not any(item.user_id == user.pk for item in targets):
        return context
    options = tuple(
        {"profile": item.profile, "label": item.get_profile_display()}
        for item in targets
        if item.user_id != user.pk
    )
    context["profile_switch_options"] = options
    context["profile_switch_origin_profile"] = switch.controller.profile
    if len(options) == 1:
        context["profile_switch_target"] = options[0]["label"]
    if user.pk != switch.controller_id:
        context["acting_as"] = _profile_label(user)
        context["acting_return"] = _profile_label(switch.controller)
    return context
