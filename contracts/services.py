from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .calculations import (
    CalculationEvidence,
    calculate_commitment_financial_position,
    calculate_contract_financial_position,
    calculate_invoice_financial_position,
    calculate_item_financial_position,
    calculate_payment_financial_position,
)
from .models import (
    BudgetCommitment,
    BudgetCommitmentEvent,
    CommitmentMovement,
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractEvent,
    ContractInvitation,
    ContractInvitationStatus,
    ContractSharingEvent,
    ContractStatus,
    FiscalSubstitution,
    FiscalSubstitutionEvent,
    FiscalSubstitutionStatus,
    ContractItem,
    ContractItemEvent,
    Invoice,
    InvoiceEvent,
    Payment,
    PaymentEvent,
    WorkOrder,
    WorkOrderAllocation,
    WorkOrderAllocationEvent,
    WorkOrderAllocationStatus,
    WorkOrderEvent,
    WorkOrderExecution,
    WorkOrderExecutionEvent,
    WorkOrderStatus,
)
from .invoice_checks import evaluate_invoice


def _format_brl(value):
    return f"{value:,.2f}".translate(str.maketrans({",": ".", ".": ","}))


def actor_is_active_fiscal(actor):
    return (
        actor.is_authenticated
        and actor.is_active
        and actor.status == AccountStatus.ACTIVE
        and actor.profile == UserProfile.FISCAL
    )


def _effective_substitution_exists(actor):
    today = timezone.localdate()
    return Exists(
        FiscalSubstitution.objects.filter(
            contract_id=OuterRef("pk"),
            substitute=actor,
            status=FiscalSubstitutionStatus.LINKED,
            starts_on__lte=today,
            ends_on__gte=today,
        )
    )


def contracts_visible_to(actor):
    queryset = Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).filter(archived_at__isnull=True)
    if not actor.is_authenticated or not actor.is_active or actor.status != AccountStatus.ACTIVE:
        return queryset.none()
    if actor.profile == UserProfile.ADMINISTRATOR and actor.has_perm(
        "contracts.view_all_contracts"
    ):
        return queryset
    read_only_access = Q(
        accesses__user=actor,
        accesses__access_type=ContractAccessType.READ_ONLY,
        accesses__status=ContractAccessStatus.ACTIVE,
    )
    if actor.profile == UserProfile.FISCAL:
        queryset = queryset.annotate(
            has_effective_substitution=_effective_substitution_exists(actor)
        )
        return queryset.filter(
            Q(responsible_fiscal=actor)
            | read_only_access
            | Q(
                has_effective_substitution=True,
                contracting_organization=actor.organization,
                contracting_organization__is_active=True,
            )
        ).distinct()
    if actor.profile == UserProfile.CONSULTATION:
        return queryset.filter(read_only_access).distinct()
    return queryset.none()


def contracts_writable_by(actor):
    if (
        not actor_is_active_fiscal(actor)
        or not actor.organization_id
        or not actor.organization.is_active
    ):
        return Contract.objects.none()
    return Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).annotate(
        has_effective_substitution=_effective_substitution_exists(actor)
    ).filter(
        archived_at__isnull=True
    ).exclude(
        status__in=(ContractStatus.CLOSED, ContractStatus.CANCELED)
    ).filter(
        contracting_organization=actor.organization,
        contracting_organization__is_active=True,
    ).filter(
        Q(responsible_fiscal=actor) | Q(has_effective_substitution=True)
    )


def contracts_managed_by(actor):
    if (
        not actor_is_active_fiscal(actor)
        or not actor.organization_id
        or not actor.organization.is_active
    ):
        return Contract.objects.none()
    return Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).filter(
        archived_at__isnull=True
    ).exclude(
        status__in=(ContractStatus.CLOSED, ContractStatus.CANCELED)
    ).filter(
        responsible_fiscal=actor,
        contracting_organization=actor.organization,
        contracting_organization__is_active=True,
    )


def contracts_lifecycle_managed_by(actor):
    queryset = Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).filter(archived_at__isnull=True)
    if (
        actor.is_authenticated
        and actor.is_active
        and actor.status == AccountStatus.ACTIVE
        and actor.profile == UserProfile.ADMINISTRATOR
        and actor.has_perm("contracts.view_all_contracts")
    ):
        return queryset
    if (
        actor_is_active_fiscal(actor)
        and actor.organization_id
        and actor.organization.is_active
    ):
        return queryset.filter(
            responsible_fiscal=actor,
            contracting_organization=actor.organization,
            contracting_organization__is_active=True,
        )
    return queryset.none()


def archived_contracts_managed_by(actor):
    queryset = Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal", "archived_by"
    ).filter(archived_at__isnull=False)
    if (
        actor.is_authenticated
        and actor.is_active
        and actor.status == AccountStatus.ACTIVE
        and actor.profile == UserProfile.ADMINISTRATOR
        and actor.has_perm("contracts.view_all_contracts")
    ):
        return queryset
    if (
        actor_is_active_fiscal(actor)
        and actor.organization_id
        and actor.organization.is_active
    ):
        return queryset.filter(
            responsible_fiscal=actor,
            contracting_organization=actor.organization,
        )
    return queryset.none()


def contracts_exportable_by(actor):
    queryset = Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).filter(archived_at__isnull=True)
    if not actor.is_authenticated or not actor.is_active or actor.status != AccountStatus.ACTIVE:
        return queryset.none()
    if actor.profile == UserProfile.ADMINISTRATOR and actor.has_perm(
        "contracts.view_all_contracts"
    ):
        return queryset
    if actor_is_active_fiscal(actor) and actor.organization_id:
        return queryset.annotate(
            has_effective_substitution=_effective_substitution_exists(actor)
        ).filter(
            contracting_organization=actor.organization,
            contracting_organization__is_active=True,
        ).filter(
            Q(responsible_fiscal=actor) | Q(has_effective_substitution=True)
        )
    return queryset.none()


def contracts_with_access_management_visible_to(actor):
    queryset = Contract.objects.select_related(
        "contracting_organization", "responsible_fiscal"
    ).filter(archived_at__isnull=True)
    if not actor.is_authenticated or not actor.is_active:
        return queryset.none()
    if actor.profile == UserProfile.ADMINISTRATOR and actor.has_perm(
        "contracts.view_all_contracts"
    ):
        return queryset
    return queryset.filter(responsible_fiscal=actor)


def contract_is_read_only_for(actor, contract):
    if not actor.is_authenticated or contract.responsible_fiscal_id == actor.pk:
        return False
    if contracts_writable_by(actor).filter(pk=contract.pk).exists():
        return False
    return ContractAccess.objects.filter(
        contract=contract,
        user=actor,
        access_type=ContractAccessType.READ_ONLY,
        status=ContractAccessStatus.ACTIVE,
    ).exists()


def actor_can_administer_all_contract_accesses(actor):
    return (
        actor.is_authenticated
        and actor.is_active
        and actor.status == AccountStatus.ACTIVE
        and actor.profile == UserProfile.ADMINISTRATOR
        and actor.has_perm("contracts.view_all_contracts")
    )


def revocable_accesses_by(actor):
    queryset = ContractAccess.objects.select_related(
        "contract", "user", "granted_by", "revoked_by"
    ).filter(status=ContractAccessStatus.ACTIVE)
    if actor_can_administer_all_contract_accesses(actor):
        return queryset
    if actor_is_active_fiscal(actor):
        return queryset.filter(granted_by=actor)
    return queryset.none()


def cancelable_invitations_by(actor):
    queryset = ContractInvitation.objects.select_related(
        "contract", "invited_by", "accepted_by"
    ).filter(status=ContractInvitationStatus.PENDING)
    if actor_can_administer_all_contract_accesses(actor):
        return queryset
    if actor_is_active_fiscal(actor):
        return queryset.filter(invited_by=actor)
    return queryset.none()


def revocable_fiscal_substitutions_by(actor):
    queryset = FiscalSubstitution.objects.select_related(
        "contract", "substitute", "created_by", "revoked_by"
    ).filter(
        status__in=(
            FiscalSubstitutionStatus.PENDING_ACCOUNT,
            FiscalSubstitutionStatus.LINKED,
        )
    )
    if actor_can_administer_all_contract_accesses(actor):
        return queryset
    if actor_is_active_fiscal(actor):
        return queryset.filter(contract__responsible_fiscal=actor)
    return queryset.none()


@transaction.atomic
def revoke_contract_access(*, access_id, contract_id, actor):
    access = (
        revocable_accesses_by(actor)
        .select_for_update(of=("self",))
        .get(pk=access_id, contract_id=contract_id)
    )
    revoked_at = timezone.now()
    access.status = ContractAccessStatus.REVOKED
    access.revoked_by = actor
    access.revoked_at = revoked_at
    access.save(update_fields=("status", "revoked_by", "revoked_at"))
    ContractSharingEvent.objects.create(
        event_type=ContractSharingEvent.EventType.ACCESS_REVOKED,
        contract=access.contract,
        access=access,
        actor=actor,
        details={
            "usuario_id": access.user_id,
            "concedido_por_id": access.granted_by_id,
            "revogado_em": revoked_at.isoformat(),
        },
    )
    return access


@transaction.atomic
def cancel_contract_invitation(*, invitation_id, contract_id, actor):
    invitation = (
        cancelable_invitations_by(actor)
        .select_for_update(of=("self",))
        .get(pk=invitation_id, contract_id=contract_id)
    )
    invitation.status = ContractInvitationStatus.CANCELED
    invitation.save(update_fields=("status",))
    ContractSharingEvent.objects.create(
        event_type=ContractSharingEvent.EventType.INVITATION_CANCELED,
        contract=invitation.contract,
        invitation=invitation,
        actor=actor,
        details={"email": invitation.email},
    )
    return invitation


def _create_pending_contract_invitation(*, contract, actor, email):
    if ContractInvitation.objects.filter(
        contract=contract,
        email=email,
        status=ContractInvitationStatus.PENDING,
    ).exists():
        raise ValidationError("Já existe convite pendente para este e-mail.")
    invitation = ContractInvitation.objects.create(
        contract=contract,
        email=email,
        access_type=ContractAccessType.READ_ONLY,
        invited_by=actor,
        status=ContractInvitationStatus.PENDING,
    )
    ContractSharingEvent.objects.create(
        event_type=ContractSharingEvent.EventType.INVITATION_CREATED,
        contract=contract,
        invitation=invitation,
        actor=actor,
        details={"email": email, "tipo": ContractAccessType.READ_ONLY},
    )
    return None, invitation


@transaction.atomic
def share_contract_read_only(*, contract_id, actor, email, confirm_regrant=False):
    contract = contracts_managed_by(actor).select_for_update().get(pk=contract_id)
    normalized_email = get_user_model().objects.normalize_login_email(email)
    if not normalized_email:
        raise ValidationError("Informe o e-mail da pessoa.")
    if normalized_email == actor.email.casefold():
        raise ValidationError("O Fiscal responsável já possui acesso ao contrato.")

    user = (
        get_user_model().objects.select_for_update()
        .filter(email__iexact=normalized_email)
        .first()
    )
    if user:
        if user.profile == UserProfile.ADMINISTRATOR and user.is_active_administrator:
            raise ValidationError("O Administrador já possui consulta administrativa.")
        if (
            user.archived_at
            or user.status
            in (AccountStatus.INACTIVE, AccountStatus.BLOCKED, AccountStatus.REJECTED)
        ):
            raise ValidationError(
                "Esta conta precisa ser regularizada pelo Administrador antes de receber acesso."
            )
        if user.status == AccountStatus.PENDING_APPROVAL or not user.is_active:
            return _create_pending_contract_invitation(
                contract=contract,
                actor=actor,
                email=normalized_email,
            )

        access = ContractAccess.objects.select_for_update().filter(
            contract=contract, user=user
        ).first()
        reactivated = False
        if access:
            if access.status == ContractAccessStatus.ACTIVE:
                raise ValidationError("Esta conta já possui acesso ao contrato.")
            if not confirm_regrant:
                raise ValidationError(
                    "Este acesso foi revogado. Marque a confirmação para concedê-lo novamente."
                )
            access.status = ContractAccessStatus.ACTIVE
            access.access_type = ContractAccessType.READ_ONLY
            access.granted_by = actor
            access.granted_at = timezone.now()
            access.revoked_by = None
            access.revoked_at = None
            access.save(
                update_fields=(
                    "status",
                    "access_type",
                    "granted_by",
                    "granted_at",
                    "revoked_by",
                    "revoked_at",
                )
            )
            reactivated = True
        else:
            access = ContractAccess.objects.create(
                contract=contract,
                user=user,
                access_type=ContractAccessType.READ_ONLY,
                status=ContractAccessStatus.ACTIVE,
                granted_by=actor,
            )
        pending = ContractInvitation.objects.select_for_update().filter(
            contract=contract,
            email=normalized_email,
            status=ContractInvitationStatus.PENDING,
        ).first()
        if pending:
            pending.status = ContractInvitationStatus.ACCEPTED
            pending.accepted_by = user
            pending.accepted_at = timezone.now()
            pending.save(update_fields=("status", "accepted_by", "accepted_at"))
        ContractSharingEvent.objects.create(
            event_type=ContractSharingEvent.EventType.ACCESS_GRANTED,
            contract=contract,
            access=access,
            invitation=pending,
            actor=actor,
            details={
                "usuario_id": user.pk,
                "tipo": ContractAccessType.READ_ONLY,
                "reativacao": reactivated,
            },
        )
        return access, pending

    return _create_pending_contract_invitation(
        contract=contract,
        actor=actor,
        email=normalized_email,
    )


@transaction.atomic
def accept_pending_contract_invitations(user):
    if (
        user.status != AccountStatus.ACTIVE
        or not user.is_active
        or user.archived_at
    ):
        return ()
    invitations = list(
        ContractInvitation.objects.select_for_update()
        .filter(email__iexact=user.email, status=ContractInvitationStatus.PENDING)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .select_related("contract", "invited_by")
    )
    for invitation in invitations:
        access = ContractAccess.objects.select_for_update().filter(
            contract=invitation.contract, user=user
        ).first()
        created = access is None
        reactivated = False
        if access is None:
            access = ContractAccess.objects.create(
                contract=invitation.contract,
                user=user,
                access_type=ContractAccessType.READ_ONLY,
                status=ContractAccessStatus.ACTIVE,
                granted_by=invitation.invited_by,
            )
        elif access.status == ContractAccessStatus.REVOKED:
            access.status = ContractAccessStatus.ACTIVE
            access.access_type = ContractAccessType.READ_ONLY
            access.granted_by = invitation.invited_by
            access.granted_at = timezone.now()
            access.revoked_by = None
            access.revoked_at = None
            access.save(
                update_fields=(
                    "status",
                    "access_type",
                    "granted_by",
                    "granted_at",
                    "revoked_by",
                    "revoked_at",
                )
            )
            reactivated = True
        invitation.status = ContractInvitationStatus.ACCEPTED
        invitation.accepted_by = user
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=("status", "accepted_by", "accepted_at"))
        ContractSharingEvent.objects.create(
            event_type=ContractSharingEvent.EventType.INVITATION_ACCEPTED,
            contract=invitation.contract,
            access=access,
            invitation=invitation,
            actor=user,
            details={
                "acesso_criado": created,
                "acesso_reativado": reactivated,
                "usuario_id": user.pk,
            },
        )
    return tuple(invitations)


@transaction.atomic
def create_fiscal_substitution(*, contract_id, actor, email, starts_on, ends_on):
    contract = contracts_managed_by(actor).select_for_update().get(pk=contract_id)
    normalized_email = get_user_model().objects.normalize_login_email(email)
    if not normalized_email:
        raise ValidationError("Informe o e-mail do Fiscal substituto.")
    if normalized_email == actor.email.casefold():
        raise ValidationError("O Fiscal titular não pode substituir a si próprio.")
    if ends_on < starts_on:
        raise ValidationError("O fim da substituição não pode anteceder o início.")
    if ends_on < timezone.localdate():
        raise ValidationError("O fim da substituição não pode estar no passado.")
    if starts_on < contract.validity_start or ends_on > contract.validity_end:
        raise ValidationError(
            "O período da substituição deve estar dentro da vigência do contrato."
        )
    if FiscalSubstitution.objects.select_for_update().filter(
        contract=contract,
        status__in=(
            FiscalSubstitutionStatus.PENDING_ACCOUNT,
            FiscalSubstitutionStatus.LINKED,
        ),
        starts_on__lte=ends_on,
        ends_on__gte=starts_on,
    ).exists():
        raise ValidationError(
            "Já existe substituição pendente ou vinculada nesse período."
        )

    user = (
        get_user_model().objects.select_for_update()
        .filter(email__iexact=normalized_email)
        .first()
    )
    substitute = None
    status = FiscalSubstitutionStatus.PENDING_ACCOUNT
    linked_at = None
    if user:
        if user.profile != UserProfile.FISCAL:
            raise ValidationError("A conta substituta deve possuir perfil Fiscal.")
        if (
            user.archived_at
            or user.status
            in (AccountStatus.INACTIVE, AccountStatus.BLOCKED, AccountStatus.REJECTED)
        ):
            raise ValidationError(
                "Esta conta precisa ser regularizada pelo Administrador antes da substituição."
            )
        if user.status == AccountStatus.ACTIVE and user.is_active:
            if user.organization_id != contract.contracting_organization_id:
                raise ValidationError(
                    "O Fiscal substituto deve pertencer à organização do contrato."
                )
            substitute = user
            status = FiscalSubstitutionStatus.LINKED
            linked_at = timezone.now()

    substitution = FiscalSubstitution.objects.create(
        contract=contract,
        substitute=substitute,
        email=normalized_email,
        starts_on=starts_on,
        ends_on=ends_on,
        status=status,
        created_by=actor,
        linked_at=linked_at,
    )
    FiscalSubstitutionEvent.objects.create(
        event_type=FiscalSubstitutionEvent.EventType.CREATED,
        substitution=substitution,
        contract=contract,
        actor=actor,
        details={
            "email": normalized_email,
            "inicio": starts_on.isoformat(),
            "fim": ends_on.isoformat(),
            "vinculado_imediatamente": bool(substitute),
        },
    )
    if substitute:
        FiscalSubstitutionEvent.objects.create(
            event_type=FiscalSubstitutionEvent.EventType.LINKED,
            substitution=substitution,
            contract=contract,
            actor=actor,
            details={"substituto_id": substitute.pk, "origem": "conta_ativa"},
        )
    return substitution


@transaction.atomic
def link_pending_fiscal_substitutions(user):
    if (
        user.profile != UserProfile.FISCAL
        or user.status != AccountStatus.ACTIVE
        or not user.is_active
        or user.archived_at
        or not user.organization_id
    ):
        return ()
    substitutions = list(
        FiscalSubstitution.objects.select_for_update()
        .filter(
            email__iexact=user.email,
            status=FiscalSubstitutionStatus.PENDING_ACCOUNT,
            contract__contracting_organization_id=user.organization_id,
            ends_on__gte=timezone.localdate(),
        )
        .select_related("contract")
    )
    now = timezone.now()
    for substitution in substitutions:
        substitution.substitute = user
        substitution.status = FiscalSubstitutionStatus.LINKED
        substitution.linked_at = now
        substitution.save(update_fields=("substitute", "status", "linked_at"))
        FiscalSubstitutionEvent.objects.create(
            event_type=FiscalSubstitutionEvent.EventType.LINKED,
            substitution=substitution,
            contract=substitution.contract,
            actor=user,
            details={"substituto_id": user.pk, "origem": "aprovacao_conta"},
        )
    return tuple(substitutions)


@transaction.atomic
def revoke_fiscal_substitution(*, substitution_id, contract_id, actor):
    substitution = (
        revocable_fiscal_substitutions_by(actor)
        .select_for_update(of=("self",))
        .get(pk=substitution_id, contract_id=contract_id)
    )
    revoked_at = timezone.now()
    substitution.status = FiscalSubstitutionStatus.REVOKED
    substitution.revoked_by = actor
    substitution.revoked_at = revoked_at
    substitution.save(update_fields=("status", "revoked_by", "revoked_at"))
    FiscalSubstitutionEvent.objects.create(
        event_type=FiscalSubstitutionEvent.EventType.REVOKED,
        substitution=substitution,
        contract=substitution.contract,
        actor=actor,
        details={
            "substituto_id": substitution.substitute_id,
            "email": substitution.email,
            "revogado_em": revoked_at.isoformat(),
        },
    )
    return substitution


def require_contract_creator(actor):
    if not actor_is_active_fiscal(actor) or not actor.has_perm("contracts.add_contract"):
        raise PermissionDenied("Somente Fiscal ativo pode cadastrar contrato próprio.")
    if not actor.organization_id or not actor.organization.is_active:
        raise ValidationError("O Fiscal precisa estar vinculado a uma organização ativa.")


def contract_snapshot(contract):
    return {
        "numero": contract.number,
        "processo": contract.process_number,
        "objeto": contract.object,
        "contratante_id": contract.contracting_organization_id,
        "fornecedor": contract.supplier_name,
        "cnpj_cpf": contract.supplier_tax_id,
        "assinatura": contract.signature_date.isoformat(),
        "vigencia_inicio": contract.validity_start.isoformat(),
        "vigencia_fim": contract.validity_end.isoformat(),
        "valor_original": str(contract.original_value),
        "valor_atual": str(contract.current_value),
        "status": contract.status,
        "fiscal_responsavel_id": contract.responsible_fiscal_id,
        "observacoes": contract.notes,
        "encerrado_em": contract.closed_at.isoformat() if contract.closed_at else None,
        "encerrado_por_id": contract.closed_by_id,
        "justificativa_encerramento": contract.closure_reason,
        "arquivado_em": contract.archived_at.isoformat() if contract.archived_at else None,
        "arquivado_por_id": contract.archived_by_id,
        "justificativa_arquivamento": contract.archive_reason,
    }


CONTRACT_STRUCTURAL_FIELDS = (
    "number",
    "process_number",
    "object",
    "supplier_name",
    "supplier_tax_id",
    "signature_date",
    "validity_start",
    "validity_end",
    "original_value",
)


def contract_operational_blockers(contract, *, include_active_accesses=False):
    from api_v1.models import AssistantDraft
    from data_imports.models import SpreadsheetImport
    from documents.models import Document

    checks = (
        ("itens", contract.items.exists()),
        ("empenhos", contract.commitments.exists()),
        ("Ordens de Serviço", contract.work_orders.exists()),
        ("notas fiscais", contract.invoices.exists()),
        ("documentos", Document.objects.filter(contract=contract).exists()),
        (
            "importações de planilha",
            SpreadsheetImport.objects.filter(contract=contract).exists(),
        ),
        (
            "rascunhos da IA",
            AssistantDraft.objects.filter(contract=contract).exists(),
        ),
    )
    blockers = [label for label, exists in checks if exists]
    if include_active_accesses:
        access_checks = (
            (
                "acessos Somente leitura ativos",
                contract.accesses.filter(status=ContractAccessStatus.ACTIVE).exists(),
            ),
            (
                "convites de acesso pendentes",
                contract.invitations.filter(
                    status=ContractInvitationStatus.PENDING
                ).exists(),
            ),
            (
                "substituições de Fiscal ativas ou pendentes",
                contract.fiscal_substitutions.filter(
                    status__in=(
                        FiscalSubstitutionStatus.PENDING_ACCOUNT,
                        FiscalSubstitutionStatus.LINKED,
                    )
                ).exists(),
            ),
        )
        blockers.extend(label for label, exists in access_checks if exists)
    return tuple(blockers)


@transaction.atomic
def create_contract(*, actor, **data):
    user_model = get_user_model()
    locked_actor = user_model.objects.select_for_update().get(pk=actor.pk)
    require_contract_creator(locked_actor)
    organization = Organization.objects.select_for_update().get(
        pk=locked_actor.organization_id,
        is_active=True,
    )
    contract = Contract(
        **data,
        contracting_organization=organization,
        responsible_fiscal=locked_actor,
    )
    contract.save()
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CREATED,
        contract=contract,
        actor=locked_actor,
        details={"atual": contract_snapshot(contract)},
    )
    return contract


@transaction.atomic
def update_contract(*, contract_id, actor, **data):
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    if data.get("status") in (ContractStatus.CLOSED, ContractStatus.CANCELED):
        raise ValidationError(
            "Encerramento ou cancelamento exige o fluxo formal com confirmação."
        )
    structural_changes = [
        field
        for field in CONTRACT_STRUCTURAL_FIELDS
        if field in data and getattr(contract, field) != data[field]
    ]
    if structural_changes and contract_operational_blockers(contract):
        raise ValidationError(
            "Campos estruturais não podem ser alterados após o início da operação. "
            "Use observações, suspensão, encerramento ou o procedimento formal aplicável."
        )
    previous = contract_snapshot(contract)
    for field, value in data.items():
        setattr(contract, field, value)
    contract.save()
    current = contract_snapshot(contract)
    event_type = (
        ContractEvent.EventType.STATUS_CHANGED
        if previous["status"] != current["status"]
        else ContractEvent.EventType.UPDATED
    )
    ContractEvent.objects.create(
        event_type=event_type,
        contract=contract,
        actor=actor,
        details={"anterior": previous, "atual": current},
    )
    return contract


@transaction.atomic
def correct_contract_registration(
    *, contract_id, actor, source_reference, reason, confirmed=False, **data
):
    """Correct proven registration errors without bypassing audit or authorization."""
    if not (
        actor.is_authenticated
        and actor.is_active
        and actor.status == AccountStatus.ACTIVE
        and actor.profile == UserProfile.ADMINISTRATOR
        and actor.has_perm("contracts.view_all_contracts")
    ):
        raise PermissionDenied(
            "Somente Administrador ativo pode corrigir dados estruturais auditados."
        )
    if not confirmed:
        raise ValidationError("Confirme expressamente a correção cadastral.")
    normalized_source = " ".join((source_reference or "").split())
    normalized_reason = " ".join((reason or "").split())
    if not normalized_source:
        raise ValidationError("Informe a fonte oficial da correção.")
    if not normalized_reason:
        raise ValidationError("Informe a justificativa da correção.")
    unexpected = set(data) - set(CONTRACT_STRUCTURAL_FIELDS) - {"status", "notes"}
    if unexpected:
        raise ValidationError(
            "A correção contém campos não autorizados: " + ", ".join(sorted(unexpected))
        )
    contract = (
        contracts_lifecycle_managed_by(actor)
        .select_for_update()
        .get(pk=contract_id)
    )
    if contract.status in (ContractStatus.CLOSED, ContractStatus.CANCELED):
        raise ValidationError("Contrato encerrado ou cancelado não admite correção cadastral.")
    if data.get("status") in (ContractStatus.CLOSED, ContractStatus.CANCELED):
        raise ValidationError("Use o fluxo formal para encerrar ou cancelar o contrato.")
    previous = contract_snapshot(contract)
    for field, value in data.items():
        setattr(contract, field, value)
    contract.save()
    current = contract_snapshot(contract)
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.UPDATED,
        contract=contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": current,
            "correcao_cadastral_auditada": True,
            "fonte_oficial": normalized_source,
            "justificativa": normalized_reason,
        },
    )
    return contract


def _revoke_substitutions_for_lifecycle(*, contract, actor, reason):
    substitutions = list(
        FiscalSubstitution.objects.select_for_update().filter(
            contract=contract,
            status__in=(
                FiscalSubstitutionStatus.PENDING_ACCOUNT,
                FiscalSubstitutionStatus.LINKED,
            ),
        )
    )
    revoked_at = timezone.now()
    for substitution in substitutions:
        substitution.status = FiscalSubstitutionStatus.REVOKED
        substitution.revoked_by = actor
        substitution.revoked_at = revoked_at
        substitution.save(update_fields=("status", "revoked_by", "revoked_at"))
        FiscalSubstitutionEvent.objects.create(
            event_type=FiscalSubstitutionEvent.EventType.REVOKED,
            substitution=substitution,
            contract=contract,
            actor=actor,
            details={
                "substituto_id": substitution.substitute_id,
                "email": substitution.email,
                "revogado_em": revoked_at.isoformat(),
                "origem": reason,
            },
        )
    return tuple(substitutions)


@transaction.atomic
def close_contract(*, contract_id, actor, reason, confirmed=False):
    if not confirmed:
        raise ValidationError("Confirme expressamente o encerramento do contrato.")
    normalized_reason = " ".join((reason or "").split())
    if not normalized_reason:
        raise ValidationError("Informe a justificativa do encerramento.")
    contract = (
        contracts_lifecycle_managed_by(actor)
        .exclude(status__in=(ContractStatus.CLOSED, ContractStatus.CANCELED))
        .select_for_update()
        .get(pk=contract_id)
    )
    nonterminal_statuses = (
        WorkOrderStatus.DRAFT,
        WorkOrderStatus.OPEN,
        WorkOrderStatus.SIGNED,
        WorkOrderStatus.IN_PROGRESS,
        WorkOrderStatus.SUSPENDED,
    )
    if contract.work_orders.filter(status__in=nonterminal_statuses).exists():
        raise ValidationError(
            "Conclua ou cancele todas as Ordens de Serviço antes de encerrar o contrato."
        )
    previous = contract_snapshot(contract)
    closed_at = timezone.now()
    contract.status = ContractStatus.CLOSED
    contract.closed_at = closed_at
    contract.closed_by = actor
    contract.closure_reason = normalized_reason
    contract.save(
        update_fields=("status", "closed_at", "closed_by", "closure_reason", "updated_at")
    )
    revoked_substitutions = _revoke_substitutions_for_lifecycle(
        contract=contract,
        actor=actor,
        reason="encerramento_contrato",
    )
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.CLOSED,
        contract=contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": contract_snapshot(contract),
            "justificativa": normalized_reason,
            "substituicoes_revogadas": len(revoked_substitutions),
        },
    )
    return contract


@transaction.atomic
def transfer_contract_responsibility(
    *, contract_id, actor, email, reason, confirmed=False
):
    if not confirmed:
        raise ValidationError("Confirme expressamente a transferência do contrato.")
    normalized_reason = " ".join((reason or "").split())
    if not normalized_reason:
        raise ValidationError("Informe a justificativa da transferência.")
    contract = (
        contracts_lifecycle_managed_by(actor)
        .exclude(status__in=(ContractStatus.CLOSED, ContractStatus.CANCELED))
        .select_for_update()
        .get(pk=contract_id)
    )
    normalized_email = get_user_model().objects.normalize_login_email(email)
    if normalized_email == contract.responsible_fiscal.email.casefold():
        raise ValidationError("O e-mail informado já pertence ao Fiscal responsável.")
    new_fiscal = (
        get_user_model().objects.select_for_update()
        .filter(
            email__iexact=normalized_email,
            profile=UserProfile.FISCAL,
            status=AccountStatus.ACTIVE,
            is_active=True,
            archived_at__isnull=True,
            organization_id=contract.contracting_organization_id,
        )
        .first()
    )
    if not new_fiscal:
        raise ValidationError(
            "Informe uma conta Fiscal ativa da mesma organização do contrato."
        )
    previous = contract_snapshot(contract)
    previous_fiscal_id = contract.responsible_fiscal_id
    contract.responsible_fiscal = new_fiscal
    contract.save(update_fields=("responsible_fiscal", "updated_at"))
    revoked_substitutions = _revoke_substitutions_for_lifecycle(
        contract=contract,
        actor=actor,
        reason="transferencia_titularidade",
    )
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.RESPONSIBLE_TRANSFERRED,
        contract=contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": contract_snapshot(contract),
            "fiscal_anterior_id": previous_fiscal_id,
            "novo_fiscal_id": new_fiscal.pk,
            "justificativa": normalized_reason,
            "substituicoes_revogadas": len(revoked_substitutions),
        },
    )
    return contract


@transaction.atomic
def archive_contract(*, contract_id, actor, reason, confirmed=False):
    if not confirmed:
        raise ValidationError("Confirme expressamente o arquivamento lógico do contrato.")
    normalized_reason = " ".join((reason or "").split())
    if not normalized_reason:
        raise ValidationError("Informe a justificativa do arquivamento.")
    contract = (
        contracts_lifecycle_managed_by(actor)
        .exclude(status__in=(ContractStatus.CLOSED, ContractStatus.CANCELED))
        .select_for_update()
        .get(pk=contract_id)
    )
    blockers = contract_operational_blockers(contract, include_active_accesses=True)
    if blockers:
        raise ValidationError(
            "O contrato não pode ser arquivado porque possui: "
            + ", ".join(blockers)
            + ". Remova os vínculos pendentes permitidos ou use o encerramento formal."
        )
    previous = contract_snapshot(contract)
    contract.archived_at = timezone.now()
    contract.archived_by = actor
    contract.archive_reason = normalized_reason
    contract.save(
        update_fields=("archived_at", "archived_by", "archive_reason", "updated_at")
    )
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.ARCHIVED,
        contract=contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": contract_snapshot(contract),
            "justificativa": normalized_reason,
            "exclusao_fisica": False,
        },
    )
    return contract


@transaction.atomic
def restore_archived_contract(*, contract_id, actor, reason, confirmed=False):
    if not confirmed:
        raise ValidationError("Confirme expressamente a restauração do contrato.")
    normalized_reason = " ".join((reason or "").split())
    if not normalized_reason:
        raise ValidationError("Informe a justificativa da restauração.")
    contract = (
        archived_contracts_managed_by(actor)
        .select_for_update(of=("self",))
        .get(pk=contract_id)
    )
    previous = contract_snapshot(contract)
    contract.archived_at = None
    contract.archived_by = None
    contract.archive_reason = ""
    contract.save(
        update_fields=("archived_at", "archived_by", "archive_reason", "updated_at")
    )
    ContractEvent.objects.create(
        event_type=ContractEvent.EventType.RESTORED,
        contract=contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": contract_snapshot(contract),
            "justificativa": normalized_reason,
        },
    )
    return contract


def items_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_contractitem"):
        return ContractItem.objects.none()
    return ContractItem.objects.select_related(
        "contract",
        "contract__contracting_organization",
        "contract__responsible_fiscal",
    ).filter(contract__in=contracts_visible_to(actor))


def items_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_contractitem"):
        return ContractItem.objects.none()
    return ContractItem.objects.select_related("contract").filter(
        contract__in=contracts_writable_by(actor)
    )


def item_snapshot(item):
    return {
        "contrato_id": item.contract_id,
        "numero": item.number,
        "codigo_oficial": item.external_code,
        "descricao": item.description,
        "categoria": item.category,
        "unidade": item.unit,
        "unidade_personalizada": item.custom_unit_name,
        "quantidade_contratada": str(item.contracted_quantity),
        "quantidade_referencia_ano_contratual": (
            str(item.annual_reference_quantity)
            if item.annual_reference_quantity is not None
            else None
        ),
        "unidade_referencia_anual": item.annual_reference_unit,
        "limite_operacional_ano_contratual": (
            str(item.annual_operational_limit)
            if item.annual_operational_limit is not None
            else None
        ),
        "valor_unitario": str(item.unit_value),
        "valor_total_derivado": str(item.total_value),
        "regra_calculo": item.calculation_rule,
        "fonte_referencia": item.source_reference,
        "ativo": item.is_active,
    }


@transaction.atomic
def create_contract_item(*, contract_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm("contracts.add_contractitem"):
        raise PermissionDenied("Permissão para cadastrar item contratual necessária.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    item = ContractItem(contract=contract, created_by=actor, **data)
    item.save()
    ContractItemEvent.objects.create(
        event_type=ContractItemEvent.EventType.CREATED,
        item=item,
        contract=contract,
        actor=actor,
        details={"atual": item_snapshot(item)},
    )
    return item


@transaction.atomic
def update_contract_item(*, item_id, actor, **data):
    item = items_writable_by(actor).select_for_update().get(pk=item_id)
    proposed_annual_limit = data.get(
        "annual_operational_limit", item.annual_operational_limit
    )
    if (
        proposed_annual_limit != item.annual_operational_limit
        and item.work_orders.exists()
    ):
        raise ValidationError(
            "O limite anual não pode ser alterado após existir histórico de OS. "
            "A correção exige procedimento administrativo auditado e análise de impacto."
        )
    previous = item_snapshot(item)
    for field, value in data.items():
        setattr(item, field, value)
    item.save()
    current = item_snapshot(item)
    if previous["ativo"] != current["ativo"]:
        event_type = (
            ContractItemEvent.EventType.ACTIVATED
            if item.is_active
            else ContractItemEvent.EventType.DEACTIVATED
        )
    else:
        event_type = ContractItemEvent.EventType.UPDATED
    ContractItemEvent.objects.create(
        event_type=event_type,
        item=item,
        contract=item.contract,
        actor=actor,
        details={"anterior": previous, "atual": current},
    )
    return item


def commitments_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_budgetcommitment"):
        return BudgetCommitment.objects.none()
    return BudgetCommitment.objects.select_related(
        "contract",
        "contract__contracting_organization",
        "contract__responsible_fiscal",
    ).prefetch_related("movements").filter(contract__in=contracts_visible_to(actor))


def commitments_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.change_budgetcommitment"
    ):
        return BudgetCommitment.objects.none()
    return BudgetCommitment.objects.select_related("contract").filter(
        contract__in=contracts_writable_by(actor)
    )


def commitment_snapshot(commitment):
    return {
        "contrato_id": commitment.contract_id,
        "numero": commitment.number,
        "ped": commitment.ped,
        "data": commitment.commitment_date.isoformat(),
        "valor_inicial": str(commitment.initial_value),
        "valor_atual_derivado": str(commitment.current_value),
        "fonte": commitment.source,
        "observacao": commitment.notes,
        "ativo": commitment.is_active,
        "exercicio": commitment.fiscal_year,
        "encerrado_para_novos_rateios_em": (
            commitment.closed_for_new_allocations_at.isoformat()
            if commitment.closed_for_new_allocations_at
            else None
        ),
    }


def movement_snapshot(movement):
    return {
        "movimentacao_id": movement.pk,
        "tipo": movement.movement_type,
        "data": movement.movement_date.isoformat(),
        "valor": str(movement.amount),
        "documento_oficial": movement.document_reference,
        "observacao": movement.notes,
    }


def item_financial_position(item):
    executions = WorkOrderExecution.objects.filter(work_order__item=item).select_related(
        "work_order"
    )
    return calculate_item_financial_position(
        item_id=item.pk,
        contracted_quantity=item.contracted_quantity,
        unit_value=item.unit_value,
        used_quantity_evidence=tuple(
            CalculationEvidence(
                source_type="EXECUCAO_OS",
                source_id=str(execution.pk),
                description=f"Execução da OS {execution.work_order.number}",
                value=execution.executed_quantity,
            )
            for execution in executions
        ),
        used_value_evidence=tuple(
            CalculationEvidence(
                source_type="EXECUCAO_OS",
                source_id=str(execution.pk),
                description=f"Execução da OS {execution.work_order.number}",
                value=execution.executed_value,
            )
            for execution in executions
        ),
    )


def commitment_financial_position(commitment):
    reinforcements = []
    cancellations = []
    for movement in commitment.movements.all():
        evidence = CalculationEvidence(
            source_type="MOVIMENTACAO_EMPENHO",
            source_id=str(movement.pk),
            description=movement.get_movement_type_display(),
            value=movement.amount,
        )
        if movement.movement_type == CommitmentMovement.Type.REINFORCEMENT:
            reinforcements.append(evidence)
        else:
            cancellations.append(evidence)
    committed_allocations = tuple(
        CalculationEvidence(
            source_type="RATEIO_OS",
            source_id=str(allocation.pk),
            description=f"Rateio da OS {allocation.work_order.number}",
            value=allocation.amount,
        )
        for allocation in commitment.allocations.select_related("work_order").filter(
            status=WorkOrderAllocationStatus.ACTIVE,
            work_order__status__in=(
                WorkOrderStatus.SIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.COMPLETED,
            ),
        )
    )
    return calculate_commitment_financial_position(
        commitment_id=commitment.pk,
        initial_value=commitment.initial_value,
        reinforcement_evidence=reinforcements,
        cancellation_evidence=cancellations,
        committed_evidence=committed_allocations,
    )


def contract_financial_position(contract):
    commitments = tuple(
        CalculationEvidence(
            source_type="EMPENHO",
            source_id=str(commitment.pk),
            description=f"Empenho {commitment.number}",
            value=commitment.current_value,
        )
        for commitment in contract.commitments.filter(is_active=True).prefetch_related(
            "movements"
        )
    )
    committed_work_orders = tuple(
        CalculationEvidence(
            source_type="ORDEM_SERVICO",
            source_id=str(work_order.pk),
            description=f"OS {work_order.number}",
            value=work_order.total_value,
        )
        for work_order in contract.work_orders.select_related("item").filter(
            status__in=(
                WorkOrderStatus.SIGNED,
                WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.COMPLETED,
            )
        )
    )
    executions = tuple(
        CalculationEvidence(
            source_type="EXECUCAO_OS",
            source_id=str(execution.pk),
            description=f"Execução da OS {execution.work_order.number}",
            value=execution.executed_value,
        )
        for execution in WorkOrderExecution.objects.select_related("work_order").filter(
            work_order__contract=contract
        )
    )
    invoices = tuple(
        CalculationEvidence(
            source_type="NOTA_FISCAL",
            source_id=str(invoice.pk),
            description=f"NF {invoice.number}/{invoice.series}",
            value=invoice.gross_value,
        )
        for invoice in contract.invoices.all()
    )
    payments = tuple(
        CalculationEvidence(
            source_type="PAGAMENTO",
            source_id=str(payment.pk),
            description=f"Pagamento da NF {payment.invoice.number}/{payment.invoice.series}",
            value=payment.amount,
        )
        for payment in Payment.objects.select_related("invoice").filter(
            invoice__contract=contract
        )
    )
    # ABERTA e SUSPENSA permanecem fora do resultado até decisão expressa.
    # RASCUNHO e CANCELADA são explicitamente não comprometedoras.
    return calculate_contract_financial_position(
        contract_id=contract.pk,
        current_value=contract.current_value,
        commitment_evidence=commitments,
        committed_evidence=committed_work_orders,
        executed_evidence=executions,
        invoiced_evidence=invoices,
        paid_evidence=payments,
    )


@transaction.atomic
def create_budget_commitment(*, contract_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.add_budgetcommitment"
    ):
        raise PermissionDenied("Permissão para cadastrar empenho necessária.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    commitment = BudgetCommitment(contract=contract, created_by=actor, **data)
    commitment.save()
    BudgetCommitmentEvent.objects.create(
        event_type=BudgetCommitmentEvent.EventType.CREATED,
        commitment=commitment,
        contract=contract,
        actor=actor,
        details={"atual": commitment_snapshot(commitment)},
    )
    return commitment


@transaction.atomic
def update_budget_commitment(*, commitment_id, actor, **data):
    commitment = commitments_writable_by(actor).select_for_update(of=("self",)).get(
        pk=commitment_id
    )
    previous = commitment_snapshot(commitment)
    for field, value in data.items():
        setattr(commitment, field, value)
    commitment.save()
    reserved = _active_allocation_total_for_commitment(commitment.pk)
    if not commitment.is_active and reserved:
        raise ValidationError("Empenho com rateio ativo não pode ser inativado.")
    if reserved > commitment.current_value:
        raise ValidationError("O valor atual do empenho não pode ficar abaixo dos rateios ativos.")
    current = commitment_snapshot(commitment)
    if previous["ativo"] != current["ativo"]:
        event_type = (
            BudgetCommitmentEvent.EventType.ACTIVATED
            if commitment.is_active
            else BudgetCommitmentEvent.EventType.DEACTIVATED
        )
    else:
        event_type = BudgetCommitmentEvent.EventType.UPDATED
    BudgetCommitmentEvent.objects.create(
        event_type=event_type,
        commitment=commitment,
        contract=commitment.contract,
        actor=actor,
        details={"anterior": previous, "atual": current},
    )
    return commitment


@transaction.atomic
def create_commitment_movement(*, commitment_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.add_commitmentmovement"
    ):
        raise PermissionDenied("Permissão para movimentar empenho necessária.")
    commitment = commitments_writable_by(actor).select_for_update(of=("self",)).get(
        pk=commitment_id,
        is_active=True,
    )
    previous = commitment_snapshot(commitment)
    movement = CommitmentMovement(
        commitment=commitment,
        created_by=actor,
        **data,
    )
    if movement.movement_type == CommitmentMovement.Type.REVERSAL:
        reserved = _active_allocation_total_for_commitment(commitment.pk)
        available = commitment.current_value - reserved
        if movement.amount != available:
            raise ValidationError(
                "O estorno deve corresponder exatamente ao saldo disponível não "
                "comprometido do empenho."
            )
    movement.save()
    if _active_allocation_total_for_commitment(commitment.pk) > commitment.current_value:
        raise ValidationError("A anulação ultrapassa o saldo protegido pelos rateios ativos.")
    if movement.movement_type == CommitmentMovement.Type.REVERSAL:
        commitment.closed_for_new_allocations_at = movement.movement_date
        commitment.save(update_fields=("closed_for_new_allocations_at", "updated_at"))
    BudgetCommitmentEvent.objects.create(
        event_type=BudgetCommitmentEvent.EventType.MOVEMENT_CREATED,
        commitment=commitment,
        contract=commitment.contract,
        actor=actor,
        details={
            "anterior": previous,
            "movimentacao": movement_snapshot(movement),
            "atual": commitment_snapshot(commitment),
        },
    )
    return movement


def work_orders_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_workorder"):
        return WorkOrder.objects.none()
    return WorkOrder.objects.select_related(
        "contract",
        "item",
        "contract__contracting_organization",
        "contract__responsible_fiscal",
        "created_by",
        "canceled_by",
    ).filter(contract__in=contracts_visible_to(actor))


def work_orders_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_workorder"):
        return WorkOrder.objects.none()
    return WorkOrder.objects.select_related("contract", "item").filter(
        contract__in=contracts_writable_by(actor)
    )


def allocations_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.view_workorderallocation"
    ):
        return WorkOrderAllocation.objects.none()
    return WorkOrderAllocation.objects.select_related(
        "work_order", "commitment", "work_order__contract", "created_by", "canceled_by"
    ).filter(work_order__contract__in=contracts_visible_to(actor))


def allocations_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.change_workorderallocation"
    ):
        return WorkOrderAllocation.objects.none()
    return WorkOrderAllocation.objects.select_related(
        "work_order", "commitment", "work_order__contract"
    ).filter(work_order__contract__in=contracts_writable_by(actor))


def executions_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_workorderexecution"):
        return WorkOrderExecution.objects.none()
    return WorkOrderExecution.objects.select_related(
        "work_order", "work_order__item", "work_order__contract", "created_by"
    ).filter(work_order__contract__in=contracts_visible_to(actor))


def executions_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_workorderexecution"):
        return WorkOrderExecution.objects.none()
    return WorkOrderExecution.objects.select_related(
        "work_order", "work_order__item", "work_order__contract"
    ).filter(work_order__contract__in=contracts_writable_by(actor))


def invoices_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_invoice"):
        return Invoice.objects.none()
    return Invoice.objects.select_related(
        "contract", "work_order", "item", "allocation", "created_by"
    ).filter(contract__in=contracts_visible_to(actor))


def invoices_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_invoice"):
        return Invoice.objects.none()
    return Invoice.objects.select_related(
        "contract", "work_order", "item", "allocation"
    ).filter(contract__in=contracts_writable_by(actor))


def payments_visible_to(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.view_payment"):
        return Payment.objects.none()
    return Payment.objects.select_related(
        "invoice", "invoice__contract", "invoice__work_order", "created_by"
    ).filter(invoice__contract__in=contracts_visible_to(actor))


def payments_writable_by(actor):
    if not actor.is_authenticated or not actor.has_perm("contracts.change_payment"):
        return Payment.objects.none()
    return Payment.objects.select_related(
        "invoice", "invoice__contract", "invoice__work_order"
    ).filter(invoice__contract__in=contracts_writable_by(actor))


def allocation_snapshot(allocation):
    return {
        "os_id": allocation.work_order_id,
        "empenho_id": allocation.commitment_id,
        "valor": str(allocation.amount),
        "data": allocation.allocation_date.isoformat(),
        "status": allocation.status,
        "motivo_cancelamento": allocation.cancellation_reason,
    }


def _active_allocation_total_for_commitment(commitment_id, *, exclude_id=None):
    queryset = WorkOrderAllocation.objects.filter(
        commitment_id=commitment_id,
        status=WorkOrderAllocationStatus.ACTIVE,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return sum((allocation.amount for allocation in queryset), Decimal("0.00"))


def _active_allocation_total_for_work_order(work_order_id, *, exclude_id=None):
    queryset = WorkOrderAllocation.objects.filter(
        work_order_id=work_order_id,
        status=WorkOrderAllocationStatus.ACTIVE,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    return sum((allocation.amount for allocation in queryset), Decimal("0.00"))


def _validate_allocation_capacity(allocation, *, exclude_id=None):
    if allocation.status != WorkOrderAllocationStatus.ACTIVE:
        return
    if allocation.work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Não é permitido ativar rateio de OS cancelada.")
    if not allocation.commitment.is_active:
        raise ValidationError("Rateio ativo exige empenho ativo.")
    if allocation.commitment.closed_for_new_allocations_at:
        raise ValidationError(
            "O empenho foi encerrado por estorno e não admite novos rateios."
        )
    work_order_total = _active_allocation_total_for_work_order(
        allocation.work_order_id, exclude_id=exclude_id
    )
    if work_order_total + allocation.amount > allocation.work_order.total_value:
        excess = work_order_total + allocation.amount - allocation.work_order.total_value
        raise ValidationError(
            f"O total dos rateios ultrapassa o valor da OS em R$ {_format_brl(excess)}."
        )
    commitment_total = _active_allocation_total_for_commitment(
        allocation.commitment_id, exclude_id=exclude_id
    )
    available = allocation.commitment.current_value - commitment_total
    if allocation.amount > available:
        excess = allocation.amount - available
        raise ValidationError(
            "O valor do rateio ultrapassa o saldo disponível do empenho em "
            f"R$ {_format_brl(excess)}."
        )


@transaction.atomic
def create_work_order_allocation(*, work_order_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm(
        "contracts.add_workorderallocation"
    ):
        raise PermissionDenied("Permissão para cadastrar rateio necessária.")
    # O queryset traz contrato/item por select_related para autorização e leitura.
    # Bloquear essas junções aqui inverteria a ordem com a movimentação de empenho.
    work_order = work_orders_writable_by(actor).select_for_update(of=("self",)).get(
        pk=work_order_id
    )
    commitment = BudgetCommitment.objects.select_for_update().get(
        pk=data.pop("commitment").pk,
        contract_id=work_order.contract_id,
    )
    if data.get("status") == WorkOrderAllocationStatus.CANCELED:
        raise ValidationError("Use a ação própria para cancelar um rateio.")
    allocation = WorkOrderAllocation(
        work_order=work_order,
        commitment=commitment,
        created_by=actor,
        **data,
    )
    allocation.full_clean()
    _validate_allocation_capacity(allocation)
    allocation.save()
    WorkOrderAllocationEvent.objects.create(
        event_type=WorkOrderAllocationEvent.EventType.CREATED,
        allocation=allocation,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"atual": allocation_snapshot(allocation)},
    )
    return allocation


@transaction.atomic
def update_work_order_allocation(*, allocation_id, actor, **data):
    visible_allocation = allocations_writable_by(actor).get(pk=allocation_id)
    requested_commitment_id = data.pop("commitment").pk
    # Ordem canônica de bloqueio financeiro: OS, empenhos por PK e rateio.
    # Todas as mutações de rateio seguem essa ordem para evitar deadlocks.
    WorkOrder.objects.select_for_update().get(pk=visible_allocation.work_order_id)
    locked_commitments = {
        commitment.pk: commitment
        for commitment in BudgetCommitment.objects.select_for_update()
        .filter(
            pk__in={visible_allocation.commitment_id, requested_commitment_id},
            contract_id=visible_allocation.work_order.contract_id,
        )
        .order_by("pk")
    }
    commitment = locked_commitments.get(requested_commitment_id)
    if commitment is None:
        raise BudgetCommitment.DoesNotExist
    allocation = allocations_writable_by(actor).select_for_update().get(pk=allocation_id)
    if allocation.status == WorkOrderAllocationStatus.CANCELED:
        raise ValidationError("Rateio cancelado é somente leitura.")
    previous = allocation_snapshot(allocation)
    allocation.commitment = commitment
    for field, value in data.items():
        setattr(allocation, field, value)
    if allocation.status == WorkOrderAllocationStatus.CANCELED:
        raise ValidationError("Use a ação própria para cancelar um rateio.")
    allocation.full_clean()
    _validate_allocation_capacity(allocation, exclude_id=allocation.pk)
    allocation.save()
    current = allocation_snapshot(allocation)
    if previous["status"] != current["status"]:
        event_type = (
            WorkOrderAllocationEvent.EventType.ACTIVATED
            if allocation.status == WorkOrderAllocationStatus.ACTIVE
            else WorkOrderAllocationEvent.EventType.DEACTIVATED
        )
    else:
        event_type = WorkOrderAllocationEvent.EventType.UPDATED
    WorkOrderAllocationEvent.objects.create(
        event_type=event_type,
        allocation=allocation,
        work_order=allocation.work_order,
        contract=allocation.work_order.contract,
        actor=actor,
        details={"anterior": previous, "atual": current},
    )
    return allocation


@transaction.atomic
def cancel_work_order_allocation(*, allocation_id, actor, reason):
    visible_allocation = allocations_writable_by(actor).get(pk=allocation_id)
    reason = " ".join((reason or "").split())
    if not reason:
        raise ValidationError("Informe o motivo do cancelamento.")
    WorkOrder.objects.select_for_update().get(pk=visible_allocation.work_order_id)
    BudgetCommitment.objects.select_for_update().get(
        pk=visible_allocation.commitment_id
    )
    allocation = allocations_writable_by(actor).select_for_update().get(pk=allocation_id)
    if allocation.status == WorkOrderAllocationStatus.CANCELED:
        raise ValidationError("O rateio já está cancelado.")
    previous = allocation_snapshot(allocation)
    allocation.status = WorkOrderAllocationStatus.CANCELED
    allocation.cancellation_reason = reason
    allocation.canceled_by = actor
    allocation.canceled_at = timezone.now()
    allocation.save()
    WorkOrderAllocationEvent.objects.create(
        event_type=WorkOrderAllocationEvent.EventType.CANCELED,
        allocation=allocation,
        work_order=allocation.work_order,
        contract=allocation.work_order.contract,
        actor=actor,
        details={"anterior": previous, "atual": allocation_snapshot(allocation)},
    )
    return allocation


def execution_snapshot(execution):
    return {
        "execucao_id": execution.pk,
        "ordem_servico_id": execution.work_order_id,
        "quantidade_executada": str(execution.executed_quantity),
        "valor_executado": str(execution.executed_value),
        "data": execution.execution_date.isoformat(),
        "competencia": execution.competence,
        "observacao": execution.notes,
        "referencia_evidencia": execution.evidence_reference,
    }


def _validate_execution_capacity(execution, *, exclude_id=None):
    existing = WorkOrderExecution.objects.filter(work_order_id=execution.work_order_id)
    if exclude_id:
        existing = existing.exclude(pk=exclude_id)
    executed_quantity = sum(
        existing.values_list("executed_quantity", flat=True), Decimal("0")
    )
    executed_value = sum(
        existing.values_list("executed_value", flat=True), Decimal("0.00")
    )
    if executed_quantity + execution.executed_quantity > execution.work_order.measure:
        raise ValidationError("A execução ultrapassa a quantidade ou horas da OS.")
    if executed_value + execution.executed_value > execution.work_order.total_value:
        raise ValidationError("A execução ultrapassa o valor total da OS.")
    item_executions = WorkOrderExecution.objects.filter(
        work_order__item_id=execution.work_order.item_id
    )
    contract_executions = WorkOrderExecution.objects.filter(
        work_order__contract_id=execution.work_order.contract_id
    )
    if exclude_id:
        item_executions = item_executions.exclude(pk=exclude_id)
        contract_executions = contract_executions.exclude(pk=exclude_id)
    item_quantity = sum(
        item_executions.values_list("executed_quantity", flat=True), Decimal("0")
    )
    item_value = sum(
        item_executions.values_list("executed_value", flat=True), Decimal("0.00")
    )
    contract_value = sum(
        contract_executions.values_list("executed_value", flat=True), Decimal("0.00")
    )
    if item_quantity + execution.executed_quantity > execution.work_order.item.contracted_quantity:
        raise ValidationError("A execução ultrapassa o saldo quantitativo do item.")
    annual_limit = execution.work_order.item.annual_operational_limit
    if annual_limit is not None:
        from .periods import contract_year_periods, period_for_date

        period = period_for_date(
            contract_year_periods(execution.work_order.contract),
            execution.execution_date,
        )
        if period is None:
            raise ValidationError(
                "A data da execução está fora da vigência do contrato."
            )
        annual_executions = item_executions.filter(
            execution_date__gte=period.start_date,
            execution_date__lte=period.end_date,
        )
        annual_executed = sum(
            annual_executions.values_list("executed_quantity", flat=True),
            Decimal("0"),
        )
        if annual_executed + execution.executed_quantity > annual_limit:
            raise ValidationError(
                f"A execução ultrapassa o limite do {period.label.lower()} "
                f"({period.start_date:%d/%m/%Y} a {period.end_date:%d/%m/%Y})."
            )
    if item_value + execution.executed_value > execution.work_order.item.total_value:
        raise ValidationError("A execução ultrapassa o saldo financeiro do item.")
    if contract_value + execution.executed_value > execution.work_order.contract.current_value:
        raise ValidationError("A execução ultrapassa o valor atual do contrato.")


def _lock_execution_scope(work_order):
    contract = Contract.objects.select_for_update().get(pk=work_order.contract_id)
    item = ContractItem.objects.select_for_update().get(
        pk=work_order.item_id, contract=contract
    )
    locked_work_order = WorkOrder.objects.select_for_update().get(
        pk=work_order.pk, contract=contract, item=item
    )
    return locked_work_order


@transaction.atomic
def create_work_order_execution(*, work_order_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm("contracts.add_workorderexecution"):
        raise PermissionDenied("Permissão para registrar execução necessária.")
    visible_work_order = work_orders_writable_by(actor).get(pk=work_order_id)
    work_order = _lock_execution_scope(visible_work_order)
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Não é possível registrar execução em OS cancelada.")
    execution = WorkOrderExecution(work_order=work_order, created_by=actor, **data)
    execution.full_clean()
    _validate_execution_capacity(execution)
    execution.save()
    WorkOrderExecutionEvent.objects.create(
        event_type=WorkOrderExecutionEvent.EventType.CREATED,
        execution=execution,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"atual": execution_snapshot(execution)},
    )
    return execution


@transaction.atomic
def update_work_order_execution(*, execution_id, actor, **data):
    visible_execution = executions_writable_by(actor).get(pk=execution_id)
    visible_work_order = work_orders_writable_by(actor).get(
        pk=visible_execution.work_order_id
    )
    work_order = _lock_execution_scope(visible_work_order)
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Execução de OS cancelada é somente leitura.")
    execution = executions_writable_by(actor).select_for_update().get(pk=execution_id)
    previous = execution_snapshot(execution)
    for field, value in data.items():
        setattr(execution, field, value)
    execution.work_order = work_order
    execution.full_clean()
    _validate_execution_capacity(execution, exclude_id=execution.pk)
    execution.save()
    WorkOrderExecutionEvent.objects.create(
        event_type=WorkOrderExecutionEvent.EventType.UPDATED,
        execution=execution,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"anterior": previous, "atual": execution_snapshot(execution)},
    )
    return execution


def invoice_snapshot(invoice):
    return {
        "nota_fiscal_id": invoice.pk,
        "contrato_id": invoice.contract_id,
        "ordem_servico_id": invoice.work_order_id,
        "item_id": invoice.item_id,
        "rateio_id": invoice.allocation_id,
        "numero": invoice.number,
        "serie": invoice.series,
        "fornecedor": invoice.supplier_name,
        "cnpj_cpf": invoice.supplier_tax_id,
        "emissao": invoice.issue_date.isoformat(),
        "competencia": invoice.competence,
        "valor_bruto": str(invoice.gross_value),
        "glosa": str(invoice.deduction_value),
        "valor_aceito": str(invoice.accepted_value),
        "processo": invoice.process_number,
        "status_informado": invoice.status,
        "referencia_documento": invoice.document_reference,
        "hash_documento": invoice.document_hash,
        "observacao": invoice.notes,
    }


def work_order_invoice_position(work_order):
    evidence = tuple(
        CalculationEvidence(
            source_type="NOTA_FISCAL",
            source_id=str(invoice.pk),
            description=f"NF {invoice.number}/{invoice.series}",
            value=invoice.gross_value,
        )
        for invoice in work_order.invoices.all()
    )
    return calculate_invoice_financial_position(
        work_order_id=work_order.pk,
        work_order_value=work_order.total_value,
        invoice_evidence=evidence,
    )


def invoice_check_report(invoice):
    other_invoice_total = sum(
        Invoice.objects.filter(work_order_id=invoice.work_order_id)
        .exclude(pk=invoice.pk)
        .values_list("gross_value", flat=True),
        Decimal("0.00"),
    )
    return evaluate_invoice(
        invoice=invoice,
        other_invoice_total=other_invoice_total,
        possible_duplicate_ids=possible_duplicate_invoice_ids(invoice),
        has_active_allocations=WorkOrderAllocation.objects.filter(
            work_order_id=invoice.work_order_id,
            status=WorkOrderAllocationStatus.ACTIVE,
        ).exists(),
    )


def payment_snapshot(payment):
    return {
        "pagamento_id": payment.pk,
        "nota_fiscal_id": payment.invoice_id,
        "valor": str(payment.amount),
        "data": payment.payment_date.isoformat(),
        "competencia": payment.competence,
        "status_informado": payment.status,
        "processo": payment.process_number,
        "atesto": payment.attestation_reference,
        "raer": payment.raer_reference,
        "termo_homologacao": payment.homologation_reference,
        "comprovante": payment.evidence_reference,
        "observacao": payment.notes,
    }


def invoice_payment_position(invoice):
    evidence = tuple(
        CalculationEvidence(
            source_type="PAGAMENTO",
            source_id=str(payment.pk),
            description=f"Pagamento de {payment.payment_date.isoformat()}",
            value=payment.amount,
        )
        for payment in invoice.payments.all()
    )
    return calculate_payment_financial_position(
        invoice_id=invoice.pk,
        gross_value=invoice.gross_value,
        accepted_value=invoice.accepted_value,
        payment_evidence=evidence,
    )


def _validate_invoice_payments(invoice, *, exclude_payment_id=None, new_amount=None):
    payments = Payment.objects.filter(invoice_id=invoice.pk)
    if exclude_payment_id:
        payments = payments.exclude(pk=exclude_payment_id)
    total = sum(payments.values_list("amount", flat=True), Decimal("0.00"))
    if new_amount is not None:
        total += new_amount
    provisional_limit = min(invoice.gross_value, invoice.accepted_value)
    if total > provisional_limit:
        raise ValidationError(
            "O total pago ultrapassa o menor valor entre o bruto e o aceito informado na NF."
        )


def _lock_payment_scope(invoice):
    contract = Contract.objects.select_for_update().get(pk=invoice.contract_id)
    item = ContractItem.objects.select_for_update().get(pk=invoice.work_order.item_id)
    work_order = WorkOrder.objects.select_for_update().get(
        pk=invoice.work_order_id, contract=contract, item=item
    )
    return Invoice.objects.select_for_update().get(
        pk=invoice.pk, contract=contract, work_order=work_order
    )


@transaction.atomic
def create_payment(*, invoice_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm("contracts.add_payment"):
        raise PermissionDenied("Permissão para registrar pagamento necessária.")
    visible_invoice = invoices_writable_by(actor).get(pk=invoice_id)
    invoice = _lock_payment_scope(visible_invoice)
    if invoice.work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Não é possível registrar pagamento de NF vinculada a OS cancelada.")
    payment = Payment(invoice=invoice, created_by=actor, **data)
    payment.full_clean()
    _validate_invoice_payments(invoice, new_amount=payment.amount)
    payment.save()
    PaymentEvent.objects.create(
        event_type=PaymentEvent.EventType.CREATED,
        payment=payment,
        invoice=invoice,
        contract=invoice.contract,
        actor=actor,
        details={"atual": payment_snapshot(payment)},
    )
    return payment


@transaction.atomic
def update_payment(*, payment_id, actor, **data):
    visible_payment = payments_writable_by(actor).get(pk=payment_id)
    invoice = _lock_payment_scope(visible_payment.invoice)
    if invoice.work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Pagamento de NF vinculada a OS cancelada é somente leitura.")
    payment = payments_writable_by(actor).select_for_update(of=("self",)).get(
        pk=payment_id
    )
    previous = payment_snapshot(payment)
    for field, value in data.items():
        setattr(payment, field, value)
    payment.invoice = invoice
    payment.full_clean()
    _validate_invoice_payments(
        invoice, exclude_payment_id=payment.pk, new_amount=payment.amount
    )
    payment.save()
    PaymentEvent.objects.create(
        event_type=PaymentEvent.EventType.UPDATED,
        payment=payment,
        invoice=invoice,
        contract=invoice.contract,
        actor=actor,
        details={"anterior": previous, "atual": payment_snapshot(payment)},
    )
    return payment


def possible_duplicate_invoice_ids(invoice):
    contextual = Q(
        contract_id=invoice.contract_id,
        work_order_id=invoice.work_order_id,
        number__iexact=invoice.number,
        series__iexact=invoice.series,
        supplier_name__iexact=invoice.supplier_name,
        supplier_tax_id=invoice.supplier_tax_id,
        gross_value=invoice.gross_value,
    )
    duplicate_filter = contextual
    if invoice.document_hash:
        duplicate_filter |= Q(document_hash=invoice.document_hash)
    queryset = Invoice.objects.filter(duplicate_filter)
    if invoice.pk:
        queryset = queryset.exclude(pk=invoice.pk)
    return tuple(queryset.order_by("pk").values_list("pk", flat=True))


def _validate_invoice_capacity(invoice, *, exclude_id=None):
    existing = Invoice.objects.filter(work_order_id=invoice.work_order_id)
    if exclude_id:
        existing = existing.exclude(pk=exclude_id)
    already_invoiced = sum(
        existing.values_list("gross_value", flat=True), Decimal("0.00")
    )
    if already_invoiced + invoice.gross_value > invoice.work_order.total_value:
        raise ValidationError(
            "O total bruto das Notas Fiscais ultrapassa o valor objetivo da OS."
        )


def _lock_invoice_scope(work_order):
    contract = Contract.objects.select_for_update().get(pk=work_order.contract_id)
    item = ContractItem.objects.select_for_update().get(
        pk=work_order.item_id, contract=contract
    )
    return WorkOrder.objects.select_for_update().get(
        pk=work_order.pk, contract=contract, item=item
    )


@transaction.atomic
def create_invoice(*, work_order_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm("contracts.add_invoice"):
        raise PermissionDenied("Permissão para cadastrar Nota Fiscal necessária.")
    visible_work_order = work_orders_writable_by(actor).get(pk=work_order_id)
    work_order = _lock_invoice_scope(visible_work_order)
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Não é possível cadastrar Nota Fiscal em OS cancelada.")
    invoice = Invoice(
        contract=work_order.contract,
        work_order=work_order,
        created_by=actor,
        **data,
    )
    invoice.full_clean()
    _validate_invoice_capacity(invoice)
    invoice.save()
    duplicate_ids = possible_duplicate_invoice_ids(invoice)
    InvoiceEvent.objects.create(
        event_type=InvoiceEvent.EventType.CREATED,
        invoice=invoice,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"atual": invoice_snapshot(invoice), "possiveis_duplicatas": duplicate_ids},
    )
    invoice.possible_duplicate_ids = duplicate_ids
    return invoice


@transaction.atomic
def update_invoice(*, invoice_id, actor, **data):
    visible_invoice = invoices_writable_by(actor).get(pk=invoice_id)
    visible_work_order = work_orders_writable_by(actor).get(
        pk=visible_invoice.work_order_id
    )
    work_order = _lock_invoice_scope(visible_work_order)
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("Nota Fiscal de OS cancelada é somente leitura.")
    invoice = invoices_writable_by(actor).select_for_update(of=("self",)).get(
        pk=invoice_id
    )
    previous = invoice_snapshot(invoice)
    for field, value in data.items():
        setattr(invoice, field, value)
    invoice.contract = work_order.contract
    invoice.work_order = work_order
    invoice.full_clean()
    _validate_invoice_capacity(invoice, exclude_id=invoice.pk)
    _validate_invoice_payments(invoice)
    invoice.save()
    duplicate_ids = possible_duplicate_invoice_ids(invoice)
    InvoiceEvent.objects.create(
        event_type=InvoiceEvent.EventType.UPDATED,
        invoice=invoice,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={
            "anterior": previous,
            "atual": invoice_snapshot(invoice),
            "possiveis_duplicatas": duplicate_ids,
        },
    )
    invoice.possible_duplicate_ids = duplicate_ids
    return invoice


def work_order_snapshot(work_order):
    return {
        "contrato_id": work_order.contract_id,
        "item_id": work_order.item_id,
        "numero": work_order.number,
        "descricao": work_order.description,
        "quantidade": str(work_order.quantity) if work_order.quantity is not None else None,
        "horas": str(work_order.hours) if work_order.hours is not None else None,
        "valor_unitario_referencia": str(work_order.unit_value),
        "unidade_referencia": work_order.unit_name,
        "valor_total_derivado": str(work_order.total_value),
        "responsavel": work_order.responsible,
        "data_abertura": work_order.opening_date.isoformat(),
        "data_assinatura": (
            work_order.signature_date.isoformat() if work_order.signature_date else None
        ),
        "inicio": work_order.start_date.isoformat() if work_order.start_date else None,
        "prazo": work_order.deadline.isoformat() if work_order.deadline else None,
        "prazo_fabrica": (
            work_order.factory_deadline.isoformat() if work_order.factory_deadline else None
        ),
        "horas_gastas_informadas": (
            str(work_order.spent_hours) if work_order.spent_hours is not None else None
        ),
        "conclusao": (
            work_order.completion_date.isoformat() if work_order.completion_date else None
        ),
        "status": work_order.status,
        "efeito_financeiro": work_order.financial_effect,
        "processo": work_order.process_number,
        "acompanhamento_mensal": work_order.monthly_follow_up,
        "observacao": work_order.notes,
        "motivo_cancelamento": work_order.cancellation_reason,
        "periodo_anual": {
            key: (
                {
                    "rotulo": period.label,
                    "inicio": period.start_date.isoformat(),
                    "fim": period.end_date.isoformat(),
                }
                if period
                else None
            )
            for key, period in work_order.annual_period_context.items()
        },
    }


def _validate_work_order_capacity(work_order, *, exclude_id=None):
    if work_order.status in {WorkOrderStatus.DRAFT, WorkOrderStatus.CANCELED}:
        return
    protected_statuses = tuple(
        status
        for status in WorkOrderStatus.values
        if status not in {WorkOrderStatus.DRAFT, WorkOrderStatus.CANCELED}
    )
    existing = WorkOrder.objects.select_for_update().filter(
        contract_id=work_order.contract_id,
        status__in=protected_statuses,
    )
    if exclude_id:
        existing = existing.exclude(pk=exclude_id)
    committed_contract_value = sum(
        (record.total_value for record in existing),
        Decimal("0.00"),
    )
    if committed_contract_value + work_order.total_value > work_order.contract.current_value:
        raise ValidationError(
            "A OS ultrapassa o saldo de valor disponível do contrato."
        )
    used_measure = sum(
        (
            record.measure
            for record in existing.filter(item_id=work_order.item_id)
        ),
        Decimal("0"),
    )
    if used_measure + work_order.measure > work_order.item.contracted_quantity:
        label = "horas" if work_order.item.unit == "HORA" else "quantidade"
        raise ValidationError(
            f"A OS ultrapassa o saldo de {label} disponível do item."
        )
    annual_limit = work_order.item.annual_operational_limit
    if annual_limit is not None:
        from .periods import contract_year_periods, period_for_date

        period = period_for_date(
            contract_year_periods(work_order.contract), work_order.opening_date
        )
        if period is None:
            raise ValidationError(
                "A data de abertura da OS está fora da vigência do contrato."
            )
        annual_used = sum(
            (
                record.measure
                for record in existing.filter(
                    item_id=work_order.item_id,
                    opening_date__gte=period.start_date,
                    opening_date__lte=period.end_date,
                )
            ),
            Decimal("0"),
        )
        if annual_used + work_order.measure > annual_limit:
            raise ValidationError(
                f"A OS ultrapassa o limite do {period.label.lower()} "
                f"({period.start_date:%d/%m/%Y} a {period.end_date:%d/%m/%Y})."
            )


def _validate_work_order_allocations(work_order):
    allocated = _active_allocation_total_for_work_order(work_order.pk)
    if allocated > work_order.total_value:
        raise ValidationError("O valor da OS não pode ficar abaixo dos rateios ativos.")


def _validate_work_order_executions(work_order):
    executed_quantity = sum(
        work_order.executions.values_list("executed_quantity", flat=True), Decimal("0")
    )
    executed_value = sum(
        work_order.executions.values_list("executed_value", flat=True), Decimal("0.00")
    )
    if executed_quantity > work_order.measure:
        raise ValidationError("A OS não pode ficar abaixo da quantidade já executada.")
    if executed_value > work_order.total_value:
        raise ValidationError("A OS não pode ficar abaixo do valor já executado.")


def _validate_work_order_invoices(work_order):
    invoiced = sum(
        work_order.invoices.values_list("gross_value", flat=True), Decimal("0.00")
    )
    if invoiced > work_order.total_value:
        raise ValidationError("A OS não pode ficar abaixo do total bruto já faturado.")


@transaction.atomic
def create_work_order(*, contract_id, actor, **data):
    if not actor.is_authenticated or not actor.has_perm("contracts.add_workorder"):
        raise PermissionDenied("Permissão para cadastrar ordem de serviço necessária.")
    contract = contracts_writable_by(actor).select_for_update().get(pk=contract_id)
    item_id = data.pop("item").pk
    item = ContractItem.objects.select_for_update().get(
        pk=item_id,
        contract=contract,
        is_active=True,
    )
    if data.get("status") == WorkOrderStatus.CANCELED:
        raise ValidationError("Use a ação própria para cancelar uma OS.")
    work_order = WorkOrder(
        contract=contract,
        item=item,
        unit_value=item.unit_value,
        unit_name=item.unit_display,
        created_by=actor,
        **data,
    )
    work_order.full_clean()
    _validate_work_order_capacity(work_order)
    work_order.save()
    WorkOrderEvent.objects.create(
        event_type=WorkOrderEvent.EventType.CREATED,
        work_order=work_order,
        contract=contract,
        actor=actor,
        details={"atual": work_order_snapshot(work_order)},
    )
    return work_order


@transaction.atomic
def update_work_order(*, work_order_id, actor, **data):
    work_order = work_orders_writable_by(actor).select_for_update().get(
        pk=work_order_id
    )
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("OS cancelada é somente leitura.")
    item = data.pop("item")
    if item.pk != work_order.item_id:
        raise ValidationError("O item da OS não pode ser alterado após o cadastro.")
    if data.get("status") == WorkOrderStatus.CANCELED:
        raise ValidationError("Use a ação própria para cancelar uma OS.")
    previous = work_order_snapshot(work_order)
    for field, value in data.items():
        setattr(work_order, field, value)
    work_order.full_clean()
    _validate_work_order_capacity(work_order, exclude_id=work_order.pk)
    _validate_work_order_allocations(work_order)
    _validate_work_order_executions(work_order)
    _validate_work_order_invoices(work_order)
    work_order.save()
    current = work_order_snapshot(work_order)
    event_type = (
        WorkOrderEvent.EventType.STATUS_CHANGED
        if previous["status"] != current["status"]
        else WorkOrderEvent.EventType.UPDATED
    )
    WorkOrderEvent.objects.create(
        event_type=event_type,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"anterior": previous, "atual": current},
    )
    return work_order


@transaction.atomic
def cancel_work_order(*, work_order_id, actor, reason):
    work_order = work_orders_writable_by(actor).select_for_update().get(
        pk=work_order_id
    )
    if work_order.status == WorkOrderStatus.CANCELED:
        raise ValidationError("A OS já está cancelada.")
    if work_order.invoices.exists():
        raise ValidationError(
            "OS com Nota Fiscal exige tratamento explícito antes do cancelamento."
        )
    reason = " ".join((reason or "").split())
    if not reason:
        raise ValidationError("Informe o motivo do cancelamento.")
    previous = work_order_snapshot(work_order)
    active_allocations = list(
        WorkOrderAllocation.objects.select_for_update().filter(
            work_order=work_order,
            status=WorkOrderAllocationStatus.ACTIVE,
        )
    )
    work_order.status = WorkOrderStatus.CANCELED
    work_order.cancellation_reason = reason
    work_order.canceled_by = actor
    work_order.canceled_at = timezone.now()
    work_order.save()
    for allocation in active_allocations:
        allocation_previous = allocation_snapshot(allocation)
        allocation.status = WorkOrderAllocationStatus.INACTIVE
        allocation.save()
        WorkOrderAllocationEvent.objects.create(
            event_type=WorkOrderAllocationEvent.EventType.DEACTIVATED,
            allocation=allocation,
            work_order=work_order,
            contract=work_order.contract,
            actor=actor,
            details={
                "motivo": "Cancelamento da OS",
                "anterior": allocation_previous,
                "atual": allocation_snapshot(allocation),
            },
        )
    WorkOrderEvent.objects.create(
        event_type=WorkOrderEvent.EventType.CANCELED,
        work_order=work_order,
        contract=work_order.contract,
        actor=actor,
        details={"anterior": previous, "atual": work_order_snapshot(work_order)},
    )
    return work_order
