from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from accounts.constants import ADMIN_GROUP, CONSULTATION_GROUP


@receiver(post_migrate, dispatch_uid="organizations.ensure_admin_permission")
def ensure_admin_permission(sender, **kwargs):
    if sender.label != "organizations":
        return
    create_permissions(sender, verbosity=0)
    administrator, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    consultation, _ = Group.objects.get_or_create(name=CONSULTATION_GROUP)
    consultation.permissions.remove(
        *Permission.objects.filter(content_type__app_label="organizations")
    )
    permission = Permission.objects.get(
        content_type__app_label="organizations",
        codename="manage_organizations",
    )
    administrator.permissions.add(permission)
