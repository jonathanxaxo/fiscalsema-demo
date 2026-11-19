from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .constants import (
    ACCESS_GROUPS,
    ADMINISTRATIVE_MANAGER_GROUP,
    ADMINISTRATOR_GENERAL_GROUP,
    AUXILIARY_ADMINISTRATIVE_GROUP,
    CONTRACT_MANAGER_GROUP,
    FISCAL_TITULAR_GROUP,
    LEGACY_CONSULTATION_GROUP,
)


@receiver(post_migrate, dispatch_uid="accounts.ensure_access_groups")
def ensure_access_groups(sender, **kwargs):
    if sender.label != "accounts":
        return
    create_permissions(sender, verbosity=0)
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in ACCESS_GROUPS}
    administrator = groups[ADMINISTRATOR_GENERAL_GROUP]
    account_permissions = Permission.objects.filter(content_type__app_label="accounts")
    for name in (
        FISCAL_TITULAR_GROUP,
        AUXILIARY_ADMINISTRATIVE_GROUP,
        ADMINISTRATIVE_MANAGER_GROUP,
        CONTRACT_MANAGER_GROUP,
        LEGACY_CONSULTATION_GROUP,
    ):
        groups[name].permissions.remove(*account_permissions)
    permissions = Permission.objects.filter(
        content_type__app_label="accounts",
        codename__in=(
            "change_user",
            "view_user",
            "manage_users",
            "review_registration",
            "view_system_health",
            "view_authenticationevent",
        ),
    )
    administrator.permissions.set(permissions)
