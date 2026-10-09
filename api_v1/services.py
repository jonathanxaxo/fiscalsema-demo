import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import AccountStatus

from .models import ApiCredential


TOKEN_PREFIX = "fsl"


def _token_hash(token):
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).hexdigest()


@transaction.atomic
def create_api_credential(*, name, authorized_user, actor, expires_at=None,
                          access_mode=ApiCredential.AccessMode.READ_ONLY):
    if not actor.is_active_administrator or not actor.has_perm("accounts.manage_users"):
        raise PermissionDenied("Somente Administrador ativo pode criar credencial da API.")
    if not authorized_user.is_active or authorized_user.status != AccountStatus.ACTIVE:
        raise ValidationError("A credencial exige usuário autorizador ativo.")
    if expires_at and expires_at <= timezone.now():
        raise ValidationError("A expiração precisa estar no futuro.")
    if access_mode not in ApiCredential.AccessMode.values:
        raise ValidationError("Modo de acesso da credencial inválido.")
    prefix = secrets.token_hex(6)
    raw_token = f"{TOKEN_PREFIX}_{prefix}_{secrets.token_urlsafe(32)}"
    credential = ApiCredential.objects.create(
        name=" ".join(name.split()), token_prefix=prefix, token_hash=_token_hash(raw_token),
        authorized_user=authorized_user, created_by=actor, expires_at=expires_at,
        access_mode=access_mode,
    )
    return credential, raw_token


@transaction.atomic
def revoke_api_credential(*, credential, actor):
    if not actor.is_active_administrator or not actor.has_perm("accounts.manage_users"):
        raise PermissionDenied("Somente Administrador ativo pode revogar credencial da API.")
    locked = ApiCredential.objects.select_for_update().get(pk=credential.pk)
    if locked.revoked_at is None:
        locked.revoked_at = timezone.now()
        locked.revoked_by = actor
        locked.save(update_fields=("revoked_at", "revoked_by"))
    return locked


class AuthenticationFailure(Exception):
    def __init__(self, code="invalid_token", message="Credencial ausente ou inválida.", credential=None):
        self.code, self.message, self.credential = code, message, credential


class RateLimitExceeded(Exception):
    def __init__(self, credential):
        self.credential = credential


@transaction.atomic
def authenticate_token(raw_token):
    parts = (raw_token or "").split("_", 2)
    if len(parts) != 3 or parts[0] != TOKEN_PREFIX or not parts[1]:
        raise AuthenticationFailure()
    credential = ApiCredential.objects.select_for_update().select_related(
        "authorized_user"
    ).filter(token_prefix=parts[1]).first()
    if credential is None or not hmac.compare_digest(credential.token_hash, _token_hash(raw_token)):
        raise AuthenticationFailure()
    now = timezone.now()
    if credential.revoked_at is not None:
        raise AuthenticationFailure("revoked_token", "Credencial revogada.", credential)
    if credential.expires_at and credential.expires_at <= now:
        raise AuthenticationFailure("expired_token", "Credencial expirada.", credential)
    user = credential.authorized_user
    if not user.is_active or user.status != AccountStatus.ACTIVE:
        raise AuthenticationFailure("inactive_user", "Usuário autorizador inativo.", credential)
    if not credential.rate_window_started_at or now - credential.rate_window_started_at >= timedelta(minutes=1):
        credential.rate_window_started_at, credential.rate_window_count = now, 1
    else:
        credential.rate_window_count += 1
    if credential.rate_window_count > settings.API_RATE_LIMIT_PER_MINUTE:
        credential.save(update_fields=("rate_window_count",))
        raise RateLimitExceeded(credential)
    credential.last_used_at = now
    credential.save(update_fields=("last_used_at", "rate_window_started_at", "rate_window_count"))
    return credential, user
