"""Painel inicial do Administrador: controle de acessos do sistema.

Somente leitura e contagens. Não altera dados nem cria novas regras de
permissão; reúne informações já disponíveis nas telas administrativas.
"""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from accounts.models import (
    AccountStatus,
    AuthenticationEvent,
    LoginThrottle,
    RegistrationRequest,
    RegistrationStatus,
    User,
    UserProfile,
)
from organizations.models import Organization, Sector

RECENT_EVENTS = 8
PENDING_PREVIEW = 5


def build_admin_dashboard():
    now = timezone.now()
    users = User.objects.filter(archived_at__isnull=True)
    status_counts = dict(
        users.order_by().values_list("status").annotate(total=Count("pk"))
    )
    active = users.filter(status=AccountStatus.ACTIVE)
    pending_requests = RegistrationRequest.objects.filter(
        status=RegistrationStatus.PENDING
    ).select_related("user")

    return {
        "users_total": users.count(),
        "users_archived": User.objects.filter(archived_at__isnull=False).count(),
        "status_rows": [
            {"value": value, "label": label, "count": status_counts.get(value, 0)}
            for value, label in AccountStatus.choices
        ],
        "profile_rows": [
            {"label": label, "count": active.filter(profile=value).count()}
            for value, label in (
                (UserProfile.ADMINISTRATOR_GENERAL, UserProfile.ADMINISTRATOR_GENERAL.label),
                (UserProfile.FISCAL_TITULAR, UserProfile.FISCAL_TITULAR.label),
                (UserProfile.AUXILIARY_ADMINISTRATIVE, UserProfile.AUXILIARY_ADMINISTRATIVE.label),
                (UserProfile.ADMINISTRATIVE_MANAGER, UserProfile.ADMINISTRATIVE_MANAGER.label),
                (UserProfile.CONTRACT_MANAGER, UserProfile.CONTRACT_MANAGER.label),
            )
        ],
        "legacy_consultation_count": active.filter(
            profile=UserProfile.CONSULTATION
        ).count(),
        "pending_count": pending_requests.count(),
        "pending_preview": list(pending_requests.order_by("created_at")[:PENDING_PREVIEW]),
        "organizations_total": Organization.objects.count(),
        "organizations_active": Organization.objects.filter(is_active=True).count(),
        "sectors_total": Sector.objects.count(),
        "login_failures_24h": AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.LOGIN_FAILURE,
            created_at__gte=now - timedelta(hours=24),
        ).count(),
        "blocked_logins": LoginThrottle.objects.filter(blocked_until__gt=now).count(),
        "recent_events": list(
            AuthenticationEvent.objects.select_related("user").order_by("-created_at", "-pk")[
                :RECENT_EVENTS
            ]
        ),
    }
