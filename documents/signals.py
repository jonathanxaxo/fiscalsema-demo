from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from accounts.constants import (
    ADMINISTRATIVE_MANAGER_GROUP,
    ADMINISTRATOR_GENERAL_GROUP,
    AUXILIARY_ADMINISTRATIVE_GROUP,
    CONTRACT_MANAGER_GROUP,
    FISCAL_TITULAR_GROUP,
    LEGACY_CONSULTATION_GROUP,
)


@receiver(post_migrate, dispatch_uid="documents.ensure_permissions")
def ensure_document_permissions(sender, **kwargs):
    if sender.label != "documents":
        return
    create_permissions(sender, verbosity=0)
    administrator, _ = Group.objects.get_or_create(name=ADMINISTRATOR_GENERAL_GROUP)
    fiscal, _ = Group.objects.get_or_create(name=FISCAL_TITULAR_GROUP)
    view_permission = Permission.objects.get(
        content_type__app_label="documents", codename="view_document"
    )
    add_permission = Permission.objects.get(
        content_type__app_label="documents", codename="add_document"
    )
    administrator.permissions.add(view_permission)
    administrator.permissions.add(
        Permission.objects.get(
            content_type__app_label="documents", codename="view_documentevent"
        )
    )
    fiscal.permissions.add(view_permission, add_permission)
    document_permissions = Permission.objects.filter(content_type__app_label="documents")
    for group_name in (
        AUXILIARY_ADMINISTRATIVE_GROUP,
        ADMINISTRATIVE_MANAGER_GROUP,
        CONTRACT_MANAGER_GROUP,
        LEGACY_CONSULTATION_GROUP,
    ):
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.remove(*document_permissions)
        group.permissions.add(view_permission)
