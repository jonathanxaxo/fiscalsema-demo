from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from accounts.constants import (
    ACCESS_GROUPS,
    ADMINISTRATOR_GENERAL_GROUP,
)


@receiver(post_migrate, dispatch_uid="organizations.ensure_admin_permission")
def ensure_admin_permission(sender, **kwargs):
    if sender.label != "organizations":
        return
    create_permissions(sender, verbosity=0)
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in ACCESS_GROUPS}
    administrator = groups[ADMINISTRATOR_GENERAL_GROUP]
    organization_permissions = Permission.objects.filter(
        content_type__app_label="organizations"
    )
    for name, group in groups.items():
        if name != ADMINISTRATOR_GENERAL_GROUP:
            group.permissions.remove(*organization_permissions)
    permission = Permission.objects.get(
        content_type__app_label="organizations",
        codename="manage_organizations",
    )
    administrator.permissions.add(permission)
