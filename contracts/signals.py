from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.conf import settings
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from accounts.constants import (
    ADMINISTRATIVE_MANAGER_GROUP,
    ADMINISTRATOR_GENERAL_GROUP,
    AUXILIARY_ADMINISTRATIVE_GROUP,
    CONTRACT_MANAGER_GROUP,
    FISCAL_TITULAR_GROUP,
    LEGACY_CONSULTATION_GROUP,
)
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
    administrator, _ = Group.objects.get_or_create(name=ADMINISTRATOR_GENERAL_GROUP)
    fiscal, _ = Group.objects.get_or_create(name=FISCAL_TITULAR_GROUP)
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
                "add_contractaccess",
                "change_contractaccess",
                "view_contractinvitation",
                "add_contractinvitation",
                "change_contractinvitation",
                "view_contractsharingevent",
                "view_fiscalsubstitution",
                "change_fiscalsubstitution",
                "view_fiscalsubstitutionevent",
                "view_contractclassification",
                "view_contractitemclassification",
                "view_contractclause",
                "view_contractrule",
                "view_contractfinding",
                "view_intelligenceexecution",
                "view_contractintelligenceevent",
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
                "add_contractclassification",
                "change_contractclassification",
                "view_contractclassification",
                "add_contractitemclassification",
                "change_contractitemclassification",
                "view_contractitemclassification",
                "add_contractclause",
                "change_contractclause",
                "view_contractclause",
                "add_contractrule",
                "change_contractrule",
                "view_contractrule",
                "add_contractfinding",
                "change_contractfinding",
                "view_contractfinding",
                "add_intelligenceexecution",
                "view_intelligenceexecution",
                "view_contractintelligenceevent",
            ),
        )
    )
    contract_permissions = Permission.objects.filter(content_type__app_label="contracts")
    read_codenames = (
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
        "view_contractclassification",
        "view_contractitemclassification",
        "view_contractclause",
        "view_contractrule",
        "view_contractfinding",
        "view_intelligenceexecution",
        "view_contractintelligenceevent",
    )
    for group_name in (
        AUXILIARY_ADMINISTRATIVE_GROUP,
        ADMINISTRATIVE_MANAGER_GROUP,
        CONTRACT_MANAGER_GROUP,
        LEGACY_CONSULTATION_GROUP,
    ):
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.remove(*contract_permissions)
        group.permissions.add(*contract_permissions.filter(codename__in=read_codenames))
    auxiliary = Group.objects.get(name=AUXILIARY_ADMINISTRATIVE_GROUP)
    auxiliary.permissions.add(
        *contract_permissions.filter(codename="view_all_contracts")
    )
