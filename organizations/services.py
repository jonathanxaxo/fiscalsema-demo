from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import Organization, OrganizationEvent, Sector


def require_manager(actor):
    if not actor.is_authenticated or not actor.has_perm("organizations.manage_organizations"):
        raise PermissionDenied("Acesso administrativo necessário.")


@transaction.atomic
def create_organization(*, actor, name, is_active=True):
    require_manager(actor)
    organization = Organization(name=name, is_active=is_active, created_by=actor)
    organization.save()
    OrganizationEvent.objects.create(
        event_type=OrganizationEvent.EventType.ORGANIZATION_CREATED,
        actor=actor,
        organization=organization,
        details={"nome": organization.name, "ativa": organization.is_active},
    )
    return organization


@transaction.atomic
def update_organization(*, organization_id, actor, name, is_active):
    require_manager(actor)
    organization = Organization.objects.select_for_update().get(pk=organization_id)
    previous = {"nome": organization.name, "ativa": organization.is_active}
    organization.name = name
    organization.is_active = is_active
    organization.save()
    deactivated_sectors = 0
    deactivated_sector_ids = []
    if previous["ativa"] and not organization.is_active:
        active_sectors = Sector.objects.select_for_update().filter(
            organization=organization, is_active=True
        )
        deactivated_sector_ids = list(active_sectors.values_list("pk", flat=True))
        deactivated_sectors = active_sectors.update(
            is_active=False, updated_at=timezone.now()
        )
        for sector_id in deactivated_sector_ids:
            OrganizationEvent.objects.create(
                event_type=OrganizationEvent.EventType.SECTOR_DEACTIVATED,
                actor=actor,
                organization=organization,
                sector_id=sector_id,
                details={"origem": "inativacao_organizacao"},
            )
    if previous["ativa"] != organization.is_active:
        event_type = (
            OrganizationEvent.EventType.ORGANIZATION_ACTIVATED
            if organization.is_active
            else OrganizationEvent.EventType.ORGANIZATION_DEACTIVATED
        )
    else:
        event_type = OrganizationEvent.EventType.ORGANIZATION_UPDATED
    OrganizationEvent.objects.create(
        event_type=event_type,
        actor=actor,
        organization=organization,
        details={
            "anterior": previous,
            "atual": {"nome": organization.name, "ativa": organization.is_active},
            "setores_inativados": deactivated_sectors,
            "setores_inativados_ids": deactivated_sector_ids,
        },
    )
    return organization


@transaction.atomic
def create_sector(*, actor, organization, name, is_active=True):
    require_manager(actor)
    organization = Organization.objects.select_for_update().get(pk=organization.pk)
    sector = Sector(
        organization=organization,
        name=name,
        is_active=is_active,
        created_by=actor,
    )
    sector.save()
    OrganizationEvent.objects.create(
        event_type=OrganizationEvent.EventType.SECTOR_CREATED,
        actor=actor,
        organization=organization,
        sector=sector,
        details={"nome": sector.name, "ativo": sector.is_active},
    )
    return sector


@transaction.atomic
def update_sector(*, sector_id, actor, organization, name, is_active):
    require_manager(actor)
    sector = Sector.objects.select_for_update().select_related("organization").get(pk=sector_id)
    organization = Organization.objects.select_for_update().get(pk=organization.pk)
    previous = {
        "nome": sector.name,
        "ativo": sector.is_active,
        "organizacao_id": sector.organization_id,
    }
    if organization.pk != sector.organization_id and sector.users.exists():
        raise ValidationError(
            "Não é possível transferir um setor que possui usuários vinculados."
        )
    sector.organization = organization
    sector.name = name
    sector.is_active = is_active
    sector.save()
    if previous["ativo"] != sector.is_active:
        event_type = (
            OrganizationEvent.EventType.SECTOR_ACTIVATED
            if sector.is_active
            else OrganizationEvent.EventType.SECTOR_DEACTIVATED
        )
    else:
        event_type = OrganizationEvent.EventType.SECTOR_UPDATED
    OrganizationEvent.objects.create(
        event_type=event_type,
        actor=actor,
        organization=organization,
        sector=sector,
        details={
            "anterior": previous,
            "atual": {
                "nome": sector.name,
                "ativo": sector.is_active,
                "organizacao_id": sector.organization_id,
            },
        },
    )
    return sector


@transaction.atomic
def assign_user_organization(*, user_id, actor, organization_id, sector_id=None):
    require_manager(actor)
    if not actor.has_perm("accounts.manage_users"):
        raise PermissionDenied("Permissão para administrar usuários necessária.")
    user_model = get_user_model()
    user = user_model.objects.select_for_update().get(pk=user_id)
    from accounts.models import DemoProfileSwitchTarget

    if DemoProfileSwitchTarget.objects.filter(user=user, is_internal=True).exists():
        raise ValidationError(
            "Conta interna da demonstração só pode ser administrada pelo fluxo manual protegido."
        )
    organization = Organization.objects.select_for_update().get(
        pk=organization_id, is_active=True
    )
    sector = None
    if sector_id:
        sector = Sector.objects.select_for_update().get(
            pk=sector_id, organization=organization, is_active=True
        )
    previous = {
        "organizacao_id": user.organization_id,
        "setor_id": user.sector_id,
    }
    user.organization = organization
    user.sector = sector
    user.save(update_fields=("organization", "sector"))
    OrganizationEvent.objects.create(
        event_type=OrganizationEvent.EventType.USER_ASSIGNED,
        actor=actor,
        organization=organization,
        sector=sector,
        user=user,
        details={
            "origem": "correcao_administrativa",
            "anterior": previous,
            "atual": {
                "organizacao_id": organization.pk,
                "setor_id": sector.pk if sector else None,
            },
        },
    )
    return user
