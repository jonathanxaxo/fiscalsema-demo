from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.constants import ADMIN_GROUP, CONSULTATION_GROUP, FISCAL_GROUP
from accounts.models import AccountStatus


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="contracts.accept_pending_invitations")
def accept_pending_invitations(sender, instance, **kwargs):
    if (
        instance.status != AccountStatus.ACTIVE
        or not instance.is_active
        or instance.archived_at
    ):
        return
    from .services import (
        accept_pending_contract_invitations,
        link_pending_fiscal_substitutions,
    )

    accept_pending_contract_invitations(instance)
    link_pending_fiscal_substitutions(instance)


@receiver(post_migrate, dispatch_uid="contracts.ensure_access_permissions")
def ensure_access_permissions(sender, **kwargs):
    if sender.label != "contracts":
        return
    create_permissions(sender, verbosity=0)
    administrator, _ = Group.objects.get_or_create(name=ADMIN_GROUP)
    fiscal, _ = Group.objects.get_or_create(name=FISCAL_GROUP)
    consultation, _ = Group.objects.get_or_create(name=CONSULTATION_GROUP)
    administrator.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="contracts",
            codename__in=(
                "view_contract",
                "view_contractevent",
                "view_contractitem",
                "view_contractitemevent",
                "view_budgetcommitment",
                "view_budgetcommitmentevent",
                "view_commitmentmovement",
                "view_workorder",
                "view_workorderevent",
                "view_workorderallocation",
                "view_workorderallocationevent",
                "view_workorderexecution",
                "view_workorderexecutionevent",
                "view_invoice",
                "view_invoiceevent",
                "view_payment",
                "view_paymentevent",
                "view_all_contracts",
                "view_contractaccess",
                "change_contractaccess",
                "view_contractinvitation",
                "change_contractinvitation",
                "view_contractsharingevent",
                "view_fiscalsubstitution",
                "change_fiscalsubstitution",
                "view_fiscalsubstitutionevent",
            ),
        )
    )
    fiscal.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="contracts",
            codename__in=(
                "add_contract",
                "change_contract",
                "view_contract",
                "add_contractitem",
                "change_contractitem",
                "view_contractitem",
                "add_budgetcommitment",
                "change_budgetcommitment",
                "view_budgetcommitment",
                "add_commitmentmovement",
                "view_commitmentmovement",
                "add_workorder",
                "change_workorder",
                "view_workorder",
                "add_workorderallocation",
                "change_workorderallocation",
                "view_workorderallocation",
                "add_workorderexecution",
                "change_workorderexecution",
                "view_workorderexecution",
                "add_invoice",
                "change_invoice",
                "view_invoice",
                "add_payment",
                "change_payment",
                "view_payment",
                "add_contractaccess",
                "change_contractaccess",
                "view_contractaccess",
                "add_contractinvitation",
                "change_contractinvitation",
                "view_contractinvitation",
                "view_contractsharingevent",
                "add_fiscalsubstitution",
                "change_fiscalsubstitution",
                "view_fiscalsubstitution",
                "view_fiscalsubstitutionevent",
            ),
        )
    )
    contract_permissions = Permission.objects.filter(content_type__app_label="contracts")
    consultation.permissions.remove(*contract_permissions)
    consultation.permissions.add(
        *contract_permissions.filter(
            codename__in=(
                "view_contract",
                "view_contractitem",
                "view_budgetcommitment",
                "view_commitmentmovement",
                "view_workorder",
                "view_workorderallocation",
                "view_workorderexecution",
                "view_invoice",
                "view_payment",
            )
        )
    )
