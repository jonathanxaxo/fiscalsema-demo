"""Configuração controlada dos perfis internos usados somente na demo."""

from django.core.exceptions import ValidationError

from organizations.models import Organization

from .models import (
    ADMINISTRATOR_PROFILES,
    DEMO_SWITCH_PROFILES,
    AccountStatus,
    DemoProfileSwitch,
    DemoProfileSwitchTarget,
    User,
    UserProfile,
)

DEMO_ORGANIZATION_NAME = "SEMA/MT — Demonstração"
INTERNAL_ACCOUNT_SPECS = {
    UserProfile.FISCAL_TITULAR: (
        "perfil.fiscal@demo.invalid",
        "Fiscal Titular — perfil interno da demo",
    ),
    UserProfile.AUXILIARY_ADMINISTRATIVE: (
        "perfil.auxiliar@demo.invalid",
        "Auxiliar Administrativa — perfil interno da demo",
    ),
    UserProfile.ADMINISTRATIVE_MANAGER: (
        "perfil.gestor.administrativo@demo.invalid",
        "Gestor Administrativo — perfil interno da demo",
    ),
    UserProfile.CONTRACT_MANAGER: (
        "perfil.gestor.contrato@demo.invalid",
        "Gestor do Contrato — perfil interno da demo",
    ),
}


def ensure_demo_organization(*, actor):
    organization = actor.organization if actor.organization_id else None
    if organization and organization.is_active:
        return organization
    organization = Organization.objects.filter(
        name__iexact=DEMO_ORGANIZATION_NAME
    ).first()
    if organization is None:
        organization = Organization.objects.create(
            name=DEMO_ORGANIZATION_NAME,
            created_by=actor,
            is_active=True,
        )
    if not organization.is_active:
        raise ValidationError("A organização interna da demonstração está inativa.")
    return organization


def ensure_switch(*, controller):
    other = DemoProfileSwitch.objects.exclude(controller=controller).first()
    if other is not None:
        raise ValidationError(
            "A troca multiperfil já pertence a outra conta controladora."
        )
    switch, _created = DemoProfileSwitch.objects.get_or_create(controller=controller)
    return switch


def ensure_target(*, switch, user, is_internal=False):
    if user.profile not in DEMO_SWITCH_PROFILES:
        raise ValidationError("A conta indicada não possui perfil funcional atual.")
    existing = DemoProfileSwitchTarget.objects.filter(
        switch=switch, profile=user.profile
    ).first()
    if existing is not None:
        if existing.user_id != user.pk or existing.is_internal != is_internal:
            raise ValidationError(
                f"O perfil {user.get_profile_display()} já possui outro vínculo."
            )
        return existing
    if DemoProfileSwitchTarget.objects.filter(user=user).exists():
        raise ValidationError("A conta indicada já pertence a outra troca de perfil.")
    return DemoProfileSwitchTarget.objects.create(
        switch=switch,
        profile=user.profile,
        user=user,
        is_internal=is_internal,
    )


def ensure_internal_user(*, profile, organization):
    if profile not in INTERNAL_ACCOUNT_SPECS:
        raise ValidationError("Não existe conta interna prevista para esse perfil.")
    email, full_name = INTERNAL_ACCOUNT_SPECS[profile]
    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        if (
            user.profile != profile
            or user.status != AccountStatus.ACTIVE
            or not user.is_active
            or user.archived_at is not None
            or user.has_usable_password()
        ):
            raise ValidationError(
                f"A conta interna {email} existe, mas não atende às proteções exigidas."
            )
        return user, False

    user = User(
        email=email,
        full_name=full_name,
        organization=organization,
        organization_name=organization.name,
        profile=profile,
        status=AccountStatus.ACTIVE,
        is_superuser=False,
        must_change_password=False,
    )
    user.set_unusable_password()
    user.save()
    return user, True


def find_administrator_target(*, controller):
    if controller.profile in ADMINISTRATOR_PROFILES and controller.is_superuser:
        return controller
    administrators = list(
        User.objects.filter(
            profile__in=ADMINISTRATOR_PROFILES,
            status=AccountStatus.ACTIVE,
            is_active=True,
            is_superuser=True,
            archived_at__isnull=True,
        ).order_by("pk")[:2]
    )
    if len(administrators) != 1:
        raise ValidationError(
            "A demonstração precisa ter exatamente um Administrador Geral ativo."
        )
    return administrators[0]


def configure_all_demo_profiles(*, controller):
    if (
        controller.profile not in DEMO_SWITCH_PROFILES
        or controller.status != AccountStatus.ACTIVE
        or not controller.is_active
        or controller.archived_at is not None
    ):
        raise ValidationError("A conta controladora precisa estar ativa e ter perfil atual.")
    if controller.profile in ADMINISTRATOR_PROFILES and not controller.is_superuser:
        raise ValidationError(
            "A conta controladora com perfil Administrador Geral precisa ser superusuária."
        )

    organization = ensure_demo_organization(actor=controller)
    administrator = find_administrator_target(controller=controller)
    switch = ensure_switch(controller=controller)
    created_internal = []

    ensure_target(switch=switch, user=controller, is_internal=False)
    if administrator.pk != controller.pk:
        ensure_target(switch=switch, user=administrator, is_internal=False)

    existing_profiles = set(switch.targets.values_list("profile", flat=True))
    for profile in DEMO_SWITCH_PROFILES:
        if profile in existing_profiles:
            continue
        if profile == UserProfile.ADMINISTRATOR_GENERAL:
            target = administrator
            is_internal = False
        elif profile == controller.profile:
            target = controller
            is_internal = False
        else:
            target, created = ensure_internal_user(
                profile=profile,
                organization=organization,
            )
            is_internal = True
            if created:
                created_internal.append(target)
        ensure_target(switch=switch, user=target, is_internal=is_internal)

    targets = list(switch.targets.select_related("user"))
    if {target.profile for target in targets} != set(DEMO_SWITCH_PROFILES):
        raise ValidationError("A configuração não produziu os cinco perfis esperados.")
    for target in targets:
        if target.user.profile != target.profile:
            raise ValidationError("Uma conta-alvo não corresponde ao perfil vinculado.")
        if target.is_internal and target.user.has_usable_password():
            raise ValidationError("Uma conta interna passou a aceitar login por senha.")
    return switch, tuple(created_internal)
