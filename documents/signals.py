from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from accounts.constants import ADMIN_GROUP, CONSULTATION_GROUP, FISCAL_GROUP


@receiver(post_migrate, dispatch_uid="documents.ensure_permissions")
def ensure_document_permissions(sender, **kwargs):
    if sender.label != "documents":
        return
    create_permissions(sender, verbosity=0)
    administrator, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    fiscal, _ = Group.objects.get_or_create(name=FISCAL_GROUP)
    consultation, _ = Group.objects.get_or_create(name=CONSULTATION_GROUP)
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
    consultation.permissions.remove(*document_permissions)
    consultation.permissions.add(view_permission)
