from django.contrib.auth.models import Group, Permission
from django.contrib.auth.management import create_permissions
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .constants import ADMIN_GROUP, CONSULTATION_GROUP, FISCAL_GROUP


@receiver(post_migrate, dispatch_uid="accounts.ensure_access_groups")
def ensure_access_groups(sender, **kwargs):
    if sender.label != "accounts":
        return
    create_permissions(sender, verbosity=0)
    administrator, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    Group.objects.get_or_create(name=FISCAL_GROUP)
    consultation, _ = Group.objects.get_or_create(name=CONSULTATION_GROUP)
    consultation.permissions.remove(
        *Permission.objects.filter(content_type__app_label="accounts")
    )
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
