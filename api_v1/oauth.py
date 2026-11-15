"""Servidor OAuth do MCP remoto (Sprint 28).

- Registro dinâmico de cliente (RFC 7591) aberto, porque clientes de IA como o
  Claude se registram sozinhos. O registro não dá acesso a nada: o acesso só
  existe depois que uma pessoa entra no FiscalSema e clica em "Autorizar".
- Limites: só ``authorization_code`` (+ ``refresh_token``), só cliente público
  com PKCE, só redirecionamento https e um teto de registros por hora.
"""

import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import ApiAccessEvent

ALLOWED_GRANTS = {"authorization_code", "refresh_token"}
MAX_REDIRECT_URIS = 5


class LimitedOpenRegistration:
    """Permite o registro público, com regras mínimas e limite global por hora."""

    def has_permission(self, request) -> bool:
        from oauth2_provider.models import get_application_model

        try:
            data = json.loads(request.body or b"{}")
        except (ValueError, UnicodeDecodeError):
            return True  # o próprio endpoint responde "invalid_client_metadata"
        if not isinstance(data, dict):
            return True
        grants = data.get("grant_types", ["authorization_code"])
        if not isinstance(grants, list) or not set(grants) <= ALLOWED_GRANTS:
            return False
        if data.get("token_endpoint_auth_method", "client_secret_basic") not in {
            "none", "client_secret_basic", "client_secret_post",
        }:
            return False
        uris = data.get("redirect_uris", [])
        if not isinstance(uris, list) or not uris or len(uris) > MAX_REDIRECT_URIS:
            return False
        if not all(isinstance(uri, str) and uri.startswith("https://") for uri in uris):
            return False
        since = timezone.now() - timedelta(hours=1)
        Application = get_application_model()
        recent = Application.objects.filter(
            registration_source=Application.RegistrationSource.DCR, created__gte=since,
        ).count()
        return recent < settings.MCP_DCR_PER_HOUR


def client_details(application):
    return {
        "cliente": (application.name or "Cliente sem nome")[:120],
        "client_id": application.client_id[:16],
    }


def record_authorization(sender, request, token, **kwargs):
    """Sinal ``app_authorized``: registra a emissão de token para a pessoa."""
    user = getattr(token, "user", None)
    if user is None or token.application_id is None:
        return
    ApiAccessEvent.objects.create(
        event_type=ApiAccessEvent.EventType.CONNECTION_AUTHORIZED,
        actor=user, endpoint="/oauth/token/", method="POST", status_code=200,
        details={**client_details(token.application), "escopos": token.scope},
    )


def connections_for(user):
    """Clientes MCP com acesso ativo (token válido ou renovação possível) da pessoa."""
    from oauth2_provider.models import AccessToken, RefreshToken, get_application_model

    now = timezone.now()
    app_ids = set(
        AccessToken.objects.filter(user=user, expires__gt=now, application__isnull=False)
        .values_list("application_id", flat=True)
    ) | set(
        RefreshToken.objects.filter(user=user, revoked__isnull=True).values_list("application_id", flat=True)
    )
    connections = []
    for application in get_application_model().objects.filter(pk__in=app_ids).order_by("name", "pk"):
        scopes = set()
        for scope in AccessToken.objects.filter(user=user, application=application).values_list("scope", flat=True):
            scopes.update(scope.split())
        last = AccessToken.objects.filter(user=user, application=application).order_by("-created").first()
        connections.append({
            "application": application,
            "scopes": sorted(scopes),
            "last_token_at": last.created if last else None,
        })
    return connections


def revoke_connection(user, application):
    """Revoga todos os tokens da pessoa para o cliente e registra auditoria."""
    from oauth2_provider.models import AccessToken, Grant, RefreshToken

    refresh_count = 0
    for refresh in RefreshToken.objects.filter(user=user, application=application, revoked__isnull=True):
        refresh.revoke()
        refresh_count += 1
    access_count, _ = AccessToken.objects.filter(user=user, application=application).delete()
    Grant.objects.filter(user=user, application=application).delete()
    ApiAccessEvent.objects.create(
        event_type=ApiAccessEvent.EventType.CONNECTION_REVOKED,
        actor=user, endpoint="/conta/conexoes/", method="POST", status_code=200,
        details={**client_details(application), "tokens_renovacao_revogados": refresh_count},
    )
