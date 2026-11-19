from datetime import timedelta
from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .managers import UserManager
from .models import (
    AccountStatus,
    AuthenticationEvent,
    DemoProfileSwitchTarget,
    LoginThrottle,
    RegistrationRequest,
    RegistrationStatus,
    User,
    UserProfile,
)
from organizations.models import Organization, OrganizationEvent, Sector


def protected_hash(value, purpose):
    normalized = value.strip().casefold()
    return salted_hmac(purpose, normalized, secret=settings.SECRET_KEY, algorithm="sha256").hexdigest()


def login_identifier_hash(email):
    return protected_hash(UserManager.normalize_login_email(email), "accounts.login.identifier")


def request_source_hash(request):
    source = request.META.get("REMOTE_ADDR", "desconhecido")
    return protected_hash(source, "accounts.login.source")


def record_authentication_event(event_type, request=None, user=None, email="", details=None):
    AuthenticationEvent.objects.create(
        event_type=event_type,
        user=user,
        identifier_hash=login_identifier_hash(email) if email else "",
        source_hash=request_source_hash(request) if request else "",
        details=details or {},
    )


def is_login_blocked(email):
    identifier = login_identifier_hash(email)
    now = timezone.now()
    throttle = LoginThrottle.objects.filter(identifier_hash=identifier).first()
    return bool(throttle and throttle.blocked_until and throttle.blocked_until > now)


def record_login_failure(email):
    identifier = login_identifier_hash(email)
    now = timezone.now()
    window = timedelta(seconds=settings.AUTH_LOGIN_WINDOW_SECONDS)
    block = timedelta(seconds=settings.AUTH_LOGIN_BLOCK_SECONDS)
    with transaction.atomic():
        throttle, _ = LoginThrottle.objects.select_for_update().get_or_create(
            identifier_hash=identifier,
            defaults={"window_started_at": now},
        )
        if now - throttle.window_started_at >= window:
            throttle.failure_count = 0
            throttle.window_started_at = now
            throttle.blocked_until = None
        throttle.failure_count += 1
        if throttle.failure_count >= settings.AUTH_LOGIN_MAX_FAILURES:
            throttle.blocked_until = now + block
        throttle.save(
            update_fields=(
                "failure_count",
                "window_started_at",
                "blocked_until",
                "updated_at",
            )
        )


def clear_login_failures(email):
    LoginThrottle.objects.filter(identifier_hash=login_identifier_hash(email)).delete()


@transaction.atomic
def review_registration_request(
    request_id,
    actor,
    action,
    rejection_reason="",
    organization_id=None,
    sector_id=None,
    approved_profile=None,
):
    if not actor.is_authenticated or not actor.has_perm("accounts.review_registration"):
        raise PermissionDenied("Acesso administrativo necessário.")
    registration = RegistrationRequest.objects.select_for_update().select_related("user").get(
        pk=request_id
    )
    user = registration.user
    if registration.status != RegistrationStatus.PENDING:
        raise ValidationError("Esta solicitação já foi analisada.")
    if user.status != AccountStatus.PENDING_APPROVAL:
        raise ValidationError("A conta não está pendente de aprovação.")

    now = timezone.now()
    registration.reviewed_by = actor
    registration.reviewed_at = now
    if action == "approve":
        if not organization_id:
            raise ValidationError("Selecione a organização da pessoa usuária.")
        organization = Organization.objects.select_for_update().get(
            pk=organization_id, is_active=True
        )
        sector = None
        if sector_id:
            sector = Sector.objects.select_for_update().get(
                pk=sector_id,
                organization=organization,
                is_active=True,
            )
        registration.status = RegistrationStatus.APPROVED
        registration.rejection_reason = ""
        approved_profile = approved_profile or registration.requested_profile
        allowed_profiles = {
            UserProfile.FISCAL_TITULAR,
            UserProfile.AUXILIARY_ADMINISTRATIVE,
            UserProfile.ADMINISTRATIVE_MANAGER,
            UserProfile.CONTRACT_MANAGER,
        }
        if approved_profile not in allowed_profiles:
            raise ValidationError("Selecione um perfil funcional válido para aprovação.")
        previous_profile = user.profile
        user.profile = approved_profile
        user.status = AccountStatus.ACTIVE
        user.organization = organization
        user.sector = sector
        event_type = AuthenticationEvent.EventType.REGISTRATION_APPROVED
    elif action == "reject":
        reason = rejection_reason.strip()
        if not reason:
            raise ValidationError("Informe o motivo da rejeição.")
        registration.status = RegistrationStatus.REJECTED
        registration.rejection_reason = reason
        user.status = AccountStatus.REJECTED
        event_type = AuthenticationEvent.EventType.REGISTRATION_REJECTED
    else:
        raise ValidationError("Ação de análise inválida.")

    user.save(update_fields=("profile", "status", "organization", "sector"))
    registration.full_clean()
    registration.save(
        update_fields=("status", "reviewed_by", "reviewed_at", "rejection_reason")
    )
    record_authentication_event(
        event_type,
        user=user,
        email=user.email,
        details={
            "solicitacao_id": registration.pk,
            "autor_id": actor.pk,
            "perfil_solicitado": registration.requested_profile,
            "perfil_aprovado": user.profile,
            "perfil_anterior": previous_profile if action == "approve" else user.profile,
        },
    )
    if action == "approve":
        OrganizationEvent.objects.create(
            event_type=OrganizationEvent.EventType.USER_ASSIGNED,
            actor=actor,
            organization=organization,
            sector=sector,
            user=user,
            details={"origem": "aprovacao_cadastro"},
        )
    return registration


def _require_user_administrator(actor):
    if (
        not actor.is_authenticated
        or not actor.is_active_administrator
        or not actor.has_perm("accounts.manage_users")
    ):
        raise PermissionDenied("Acesso administrativo necessário.")


def _delete_user_sessions(user_id):
    session_keys = []
    for session in Session.objects.all().iterator():
        if str(session.get_decoded().get("_auth_user_id")) == str(user_id):
            session_keys.append(session.session_key)
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()
    return len(session_keys)


def _reject_internal_demo_account(user):
    if DemoProfileSwitchTarget.objects.filter(user=user, is_internal=True).exists():
        raise ValidationError(
            "Conta interna da demonstração só pode ser administrada pelo fluxo manual protegido."
        )


@transaction.atomic
def change_user_profile(*, user_id, actor, profile):
    """Reclassifica uma conta com auditoria e revoga vínculos incompatíveis."""
    _require_user_administrator(actor)
    allowed_profiles = {
        UserProfile.ADMINISTRATOR_GENERAL,
        UserProfile.FISCAL_TITULAR,
        UserProfile.AUXILIARY_ADMINISTRATIVE,
        UserProfile.ADMINISTRATIVE_MANAGER,
        UserProfile.CONTRACT_MANAGER,
    }
    if profile not in allowed_profiles:
        raise ValidationError("Selecione um perfil funcional atual.")

    target = User.objects.select_for_update().get(pk=user_id)
    _reject_internal_demo_account(target)
    if target.pk == actor.pk:
        raise ValidationError("Você não pode alterar o perfil da própria conta.")
    if target.archived_at:
        raise ValidationError("Restaure a conta antes de alterar o perfil.")
    if target.profile == profile:
        raise ValidationError("A conta já possui esse perfil.")

    from contracts.models import (
        Contract,
        ContractAccessStatus,
        FiscalSubstitutionStatus,
    )
    from contracts.services import revoke_contract_access, revoke_fiscal_substitution

    if target.profile in (UserProfile.FISCAL_TITULAR, UserProfile.FISCAL):
        if profile != UserProfile.FISCAL_TITULAR and Contract.objects.filter(
            responsible_fiscal=target, archived_at__isnull=True
        ).exists():
            raise ValidationError(
                "Transfira os contratos ativos deste Fiscal antes de alterar o perfil."
            )

    revoked_accesses = 0
    active_accesses_queryset = target.contract_accesses.select_for_update().filter(
        status=ContractAccessStatus.ACTIVE
    )
    if profile == UserProfile.CONTRACT_MANAGER:
        active_accesses_queryset = active_accesses_queryset.none()
    active_accesses = list(
        active_accesses_queryset.values_list("pk", "contract_id")
    )
    if active_accesses:
        for access_id, contract_id in active_accesses:
            revoke_contract_access(
                access_id=access_id, contract_id=contract_id, actor=actor
            )
            revoked_accesses += 1

    revoked_substitutions = 0
    if profile != UserProfile.FISCAL_TITULAR:
        substitutions = list(
            target.fiscal_substitutions.select_for_update()
            .filter(
                status__in=(
                    FiscalSubstitutionStatus.PENDING_ACCOUNT,
                    FiscalSubstitutionStatus.LINKED,
                )
            )
            .values_list("pk", "contract_id")
        )
        for substitution_id, contract_id in substitutions:
            revoke_fiscal_substitution(
                substitution_id=substitution_id,
                contract_id=contract_id,
                actor=actor,
            )
            revoked_substitutions += 1

    previous_profile = target.profile
    target.profile = profile
    target.save(update_fields=("profile",))
    removed_sessions = _delete_user_sessions(target.pk)
    record_authentication_event(
        AuthenticationEvent.EventType.PROFILE_CHANGED,
        user=target,
        email=target.email,
        details={
            "autor_id": actor.pk,
            "perfil_anterior": previous_profile,
            "perfil_novo": profile,
            "sessoes_encerradas": removed_sessions,
            "acessos_revogados": revoked_accesses,
            "substituicoes_revogadas": revoked_substitutions,
        },
    )
    return target


@transaction.atomic
def change_user_status(*, user_id, actor, action):
    _require_user_administrator(actor)
    target = User.objects.select_for_update().get(pk=user_id)
    _reject_internal_demo_account(target)
    if target.pk == actor.pk:
        raise ValidationError("Você não pode alterar o status da própria conta.")
    if target.archived_at:
        raise ValidationError("Restaure a conta excluída antes de alterar seu status.")

    previous_status = target.status
    if action == "deactivate":
        if target.status != AccountStatus.ACTIVE:
            raise ValidationError("Somente uma conta ativa pode ser inativada.")
        target.status = AccountStatus.INACTIVE
    elif action == "activate":
        if target.status != AccountStatus.INACTIVE:
            raise ValidationError("Somente uma conta inativa pode ser ativada.")
        target.status = AccountStatus.ACTIVE
    elif action == "block":
        if target.status not in (AccountStatus.ACTIVE, AccountStatus.INACTIVE):
            raise ValidationError("Somente uma conta ativa ou inativa pode ser bloqueada.")
        target.status = AccountStatus.BLOCKED
    elif action == "unblock":
        if target.status != AccountStatus.BLOCKED:
            raise ValidationError("Somente uma conta bloqueada pode ser desbloqueada.")
        target.status = AccountStatus.INACTIVE
    else:
        raise ValidationError("Ação de status inválida.")

    target.save(update_fields=("status",))
    removed_sessions = (
        _delete_user_sessions(target.pk)
        if action in ("deactivate", "block", "unblock")
        else 0
    )
    record_authentication_event(
        AuthenticationEvent.EventType.ACCOUNT_STATUS_CHANGED,
        user=target,
        email=target.email,
        details={
            "autor_id": actor.pk,
            "status_anterior": previous_status,
            "status_novo": target.status,
            "sessoes_encerradas": removed_sessions,
        },
    )
    return target


@transaction.atomic
def archive_user(*, user_id, actor):
    _require_user_administrator(actor)
    target = User.objects.select_for_update().get(pk=user_id)
    _reject_internal_demo_account(target)
    if target.pk == actor.pk:
        raise ValidationError("Você não pode excluir logicamente a própria conta.")
    if target.archived_at:
        raise ValidationError("Esta conta já está excluída logicamente.")
    if target.status == AccountStatus.ACTIVE:
        raise ValidationError("Inative a conta antes de excluí-la logicamente.")

    target.status = AccountStatus.INACTIVE
    target.archived_at = timezone.now()
    target.archived_by = actor
    target.save(update_fields=("status", "archived_at", "archived_by"))
    removed_sessions = _delete_user_sessions(target.pk)

    from api_v1.models import ApiCredential

    revoked_credentials = ApiCredential.objects.select_for_update().filter(
        authorized_user=target,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now(), revoked_by=actor)
    record_authentication_event(
        AuthenticationEvent.EventType.ACCOUNT_ARCHIVED,
        user=target,
        email=target.email,
        details={
            "autor_id": actor.pk,
            "sessoes_encerradas": removed_sessions,
            "credenciais_api_revogadas": revoked_credentials,
            "exclusao_fisica": False,
        },
    )
    return target


@transaction.atomic
def restore_user(*, user_id, actor):
    _require_user_administrator(actor)
    target = User.objects.select_for_update().get(pk=user_id)
    _reject_internal_demo_account(target)
    if not target.archived_at:
        raise ValidationError("Esta conta não está excluída logicamente.")
    target.archived_at = None
    target.archived_by = None
    target.status = AccountStatus.INACTIVE
    target.save(update_fields=("status", "archived_at", "archived_by"))
    record_authentication_event(
        AuthenticationEvent.EventType.ACCOUNT_RESTORED,
        user=target,
        email=target.email,
        details={"autor_id": actor.pk, "status_restaurado": AccountStatus.INACTIVE},
    )
    return target


@transaction.atomic
def archive_registration_request(*, registration_id, actor):
    if not actor.is_authenticated or not actor.has_perm("accounts.review_registration"):
        raise PermissionDenied("Acesso administrativo necessário.")
    registration = RegistrationRequest.objects.select_for_update().select_related("user").get(
        pk=registration_id
    )
    if registration.archived_at:
        raise ValidationError("Esta solicitação já está arquivada.")
    registration.archived_at = timezone.now()
    registration.archived_by = actor
    registration.save(update_fields=("archived_at", "archived_by"))
    record_authentication_event(
        AuthenticationEvent.EventType.REGISTRATION_ARCHIVED,
        user=registration.user,
        email=registration.user.email,
        details={
            "solicitacao_id": registration.pk,
            "autor_id": actor.pk,
            "status_preservado": registration.status,
        },
    )
    return registration
