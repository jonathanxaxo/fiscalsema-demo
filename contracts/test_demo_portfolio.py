import os
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from accounts.models import (
    AccountStatus,
    DemoProfileSwitchTarget,
    User,
    UserProfile,
)
from organizations.models import Organization

from .management.commands.seed_demo_portfolio import PORTFOLIO_MARKER
from .models import (
    Contract,
    ContractAccess,
    ContractAlertPolicy,
    ContractChange,
    ContractChecklistItem,
    ContractClassification,
    ContractExternalRecord,
    ContractItem,
    ContractManagementCategory,
    ContractObligation,
    ContractReceipt,
    ContractRisk,
    WorkOrder,
)
from .services import contracts_visible_to
from .tests import VALID_PASSWORD

CONTROLLER_EMAIL = "admin@exemplo.com.br"


def prepare_demo():
    output = StringIO()
    with mock.patch.dict(
        os.environ,
        {"DEMO_SWITCH_CONTROLLER_EMAIL": CONTROLLER_EMAIL},
    ):
        call_command("enable_demo_multprofile_switch", stdout=output)
        call_command("seed_demo_portfolio", stdout=output)
    return output.getvalue()


@override_settings(APP_ENVIRONMENT="demo")
class DemoPortfolioTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SEMA")
        self.admin = User.objects.create_superuser(
            email="administrador.inicial@exemplo.local",
            full_name="Administrador Inicial",
            password=VALID_PASSWORD,
        )
        self.controller = User.objects.create_user(
            email=CONTROLLER_EMAIL,
            full_name="Responsável pela demonstração",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other_fiscal = User.objects.create_user(
            email="fiscal.teste@exemplo.com.br",
            full_name="Fiscal de Teste",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other_manager = User.objects.create_user(
            email="gestor.contrato.teste@exemplo.com.br",
            full_name="Gestor do Contrato de Teste",
            password=VALID_PASSWORD,
            profile=UserProfile.CONTRACT_MANAGER,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )

    def target_user(self, profile):
        return DemoProfileSwitchTarget.objects.select_related("user").get(
            profile=profile
        ).user

    def test_creates_idempotent_classified_portfolio_for_every_active_profile(self):
        output = prepare_demo()
        self.assertIn("Carteira fictícia pronta", output)
        self.assertEqual(
            Contract.objects.filter(notes__contains=PORTFOLIO_MARKER).count(),
            5,
        )
        self.assertEqual(ContractItem.objects.count(), 15)
        self.assertEqual(WorkOrder.objects.count(), 25)
        self.assertEqual(ContractAlertPolicy.objects.count(), 5)
        self.assertEqual(ContractObligation.objects.count(), 5)
        self.assertEqual(ContractChange.objects.count(), 5)
        self.assertEqual(ContractReceipt.objects.count(), 5)
        self.assertEqual(ContractRisk.objects.count(), 5)
        self.assertEqual(ContractExternalRecord.objects.count(), 15)
        self.assertGreaterEqual(ContractChecklistItem.objects.count(), 28)
        primary_contracts = Contract.objects.filter(
            responsible_fiscal=self.controller,
            notes__contains=PORTFOLIO_MARKER,
        )
        self.assertEqual(primary_contracts.count(), 4)
        self.assertEqual(
            set(
                ContractClassification.objects.filter(
                    contract__in=primary_contracts
                ).values_list("management_category", flat=True)
            ),
            {
                ContractManagementCategory.SYSTEM,
                ContractManagementCategory.EQUIPMENT,
                ContractManagementCategory.CONTINUOUS_SERVICE,
                ContractManagementCategory.SINGLE_DELIVERY,
            },
        )

        counts_before = (
            Contract.objects.count(),
            ContractItem.objects.count(),
            WorkOrder.objects.count(),
            ContractAccess.objects.count(),
            ContractAlertPolicy.objects.count(),
            ContractObligation.objects.count(),
            ContractChange.objects.count(),
            ContractReceipt.objects.count(),
            ContractRisk.objects.count(),
            ContractChecklistItem.objects.count(),
            ContractExternalRecord.objects.count(),
        )
        prepare_demo()
        self.assertEqual(
            counts_before,
            (
                Contract.objects.count(),
                ContractItem.objects.count(),
                WorkOrder.objects.count(),
                ContractAccess.objects.count(),
                ContractAlertPolicy.objects.count(),
                ContractObligation.objects.count(),
                ContractChange.objects.count(),
                ContractReceipt.objects.count(),
                ContractRisk.objects.count(),
                ContractChecklistItem.objects.count(),
                ContractExternalRecord.objects.count(),
            ),
        )

    def test_visibility_matches_each_profile_scope(self):
        prepare_demo()
        total = Contract.objects.filter(notes__contains=PORTFOLIO_MARKER).count()
        auxiliary = self.target_user(UserProfile.AUXILIARY_ADMINISTRATIVE)
        administrative_manager = self.target_user(UserProfile.ADMINISTRATIVE_MANAGER)
        internal_contract_manager = self.target_user(UserProfile.CONTRACT_MANAGER)

        self.assertEqual(contracts_visible_to(self.admin).count(), total)
        self.assertEqual(contracts_visible_to(auxiliary).count(), total)
        self.assertEqual(contracts_visible_to(administrative_manager).count(), total)
        self.assertEqual(contracts_visible_to(self.controller).count(), 4)
        self.assertEqual(contracts_visible_to(self.other_fiscal).count(), 1)
        self.assertEqual(contracts_visible_to(internal_contract_manager).count(), 2)
        self.assertEqual(contracts_visible_to(self.other_manager).count(), 2)
