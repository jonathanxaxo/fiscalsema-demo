"""Painéis independentes dos cinco perfis funcionais (Sprint 58)."""

import os
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, User, UserProfile
from contracts.models import (
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractClassification,
    ContractManagementCategory,
    IntelligenceReviewStatus,
)
from core.notifications import build_notifications
from documents.models import Document, DocumentType, RelatedEntityType
from organizations.models import Organization

VALID_PASSWORD = "SenhaMuitoForte!2026"


class IndependentProfileDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Organização Demo")
        cls.admin = User.objects.create_superuser(
            email="admin.paineis@example.local",
            full_name="Administrador Geral",
            password=VALID_PASSWORD,
        )
        cls.fiscal = cls._user("fiscal@example.local", UserProfile.FISCAL_TITULAR)
        cls.auxiliary = cls._user(
            "auxiliar@example.local", UserProfile.AUXILIARY_ADMINISTRATIVE
        )
        cls.administrative_manager = cls._user(
            "gestor.administrativo@example.local",
            UserProfile.ADMINISTRATIVE_MANAGER,
        )
        cls.contract_manager = cls._user(
            "gestor.contrato@example.local", UserProfile.CONTRACT_MANAGER
        )
        cls.contract_a = cls._contract("DEMO-PAINEL-A/2026")
        cls.contract_b = cls._contract("DEMO-PAINEL-B/2026")
        cls.archived_contract = cls._contract("DEMO-ARQUIVADO/2026")
        Contract.objects.filter(pk=cls.archived_contract.pk).update(
            archived_at=timezone.now(),
            archived_by=cls.admin,
            archive_reason="Arquivado para teste fictício.",
        )
        ContractAccess.objects.create(
            contract=cls.contract_a,
            user=cls.contract_manager,
            access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE,
            granted_by=cls.fiscal,
        )
        ContractClassification.objects.create(
            contract=cls.contract_a,
            management_category=ContractManagementCategory.SYSTEM,
            status=IntelligenceReviewStatus.CONFIRMED,
            confirmed_by=cls.fiscal,
            confirmed_at=timezone.now(),
        )
        ContractClassification.objects.create(
            contract=cls.contract_b,
            management_category=ContractManagementCategory.EQUIPMENT,
            status=IntelligenceReviewStatus.CONFIRMED,
            confirmed_by=cls.fiscal,
            confirmed_at=timezone.now(),
        )
        Document.objects.create(
            contract=cls.contract_a,
            title="Contrato fictício catalogado",
            document_type=DocumentType.CONTRACT,
            origin="Teste automatizado",
            related_entity_type=RelatedEntityType.CONTRACT,
            file="documents/ficticio.pdf",
            original_name="ficticio.pdf",
            mime_type="application/pdf",
            file_size=100,
            sha256="a" * 64,
            uploaded_by=cls.fiscal,
        )

    @classmethod
    def _user(cls, email, profile):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0],
            password=VALID_PASSWORD,
            profile=profile,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )

    @classmethod
    def _contract(cls, number):
        return Contract.objects.create(
            number=number,
            process_number=f"PROC-{number}",
            object="Objeto exclusivamente fictício para teste",
            contracting_organization=cls.organization,
            supplier_name="Fornecedor Fictício Ltda.",
            supplier_tax_id="12345678000199",
            signature_date=date(2026, 1, 1),
            validity_start=date(2026, 1, 1),
            validity_end=date(2027, 12, 31),
            original_value=Decimal("100000.00"),
            responsible_fiscal=cls.fiscal,
        )

    def test_administrator_and_fiscal_keep_their_existing_dashboards(self):
        self.client.force_login(self.admin)
        admin_page = self.client.get(reverse("home"))
        self.assertTemplateUsed(admin_page, "core/admin_home.html")
        self.assertContains(admin_page, "Controle de acessos")

        self.client.force_login(self.fiscal)
        fiscal_page = self.client.get(reverse("home"))
        self.assertTemplateUsed(fiscal_page, "home.html")
        self.assertContains(fiscal_page, "Painel do contrato")

    def test_auxiliary_has_metadata_only_dashboard_without_archived_contracts(self):
        self.client.force_login(self.auxiliary)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/auxiliary_home.html")
        self.assertContains(page, "Painel de metadados administrativos")
        self.assertContains(page, self.contract_a.number)
        self.assertContains(page, self.contract_b.number)
        self.assertNotContains(page, self.archived_contract.number)
        self.assertContains(page, "1 metadado(s)")
        self.assertNotContains(page, "R$&nbsp;", html=False)
        self.assertNotContains(page, reverse("contracts:executive_dashboard"))

        notifications = build_notifications(self.auxiliary)
        self.assertGreaterEqual(notifications["count"], 1)
        self.assertTrue(
            all(
                item["hint"] == "Conferir metadados administrativos"
                for item in notifications["items"]
            )
        )
        self.assertTrue(
            all(item["url"].endswith("#aux-cadastros") for item in notifications["items"])
        )
        self.assertFalse(
            any("valor" in item["title"].lower() for item in notifications["items"])
        )

    def test_administrative_manager_has_consolidated_classified_portfolio(self):
        self.client.force_login(self.administrative_manager)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/administrative_manager_home.html")
        self.assertContains(page, "Painel executivo da carteira")
        self.assertContains(page, "Sistema")
        self.assertContains(page, "Equipamento")
        self.assertContains(page, self.contract_a.number)
        self.assertContains(page, self.contract_b.number)
        self.assertNotContains(page, self.archived_contract.number)
        self.assertContains(page, "R$&nbsp;200.000,00", html=False)
        self.assertContains(page, reverse("contracts:executive_dashboard"))

    def test_contract_manager_has_only_linked_contract_and_reports(self):
        self.client.force_login(self.contract_manager)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/contract_manager_home.html")
        self.assertContains(page, "Painel de acompanhamento individual")
        self.assertContains(page, "Gráfico financeiro")
        self.assertContains(page, self.contract_a.number)
        self.assertNotContains(page, self.contract_b.number)
        self.assertContains(page, reverse("contracts:report", args=[self.contract_a.pk]))
        self.assertContains(page, "Somente leitura")
        forbidden = self.client.get(reverse("home"), {"contract": self.contract_b.pk})
        self.assertEqual(forbidden.status_code, 404)


@override_settings(APP_ENVIRONMENT="demo")
class MultiProfileDashboardIntegrationTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Organização Demo")
        User.objects.create_superuser(
            email="administrador.inicial@example.local",
            full_name="Administrador Inicial",
            password=VALID_PASSWORD,
        )
        self.controller = User.objects.create_user(
            email="admin@exemplo.com.br",
            full_name="Conta controladora",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=organization,
        )
        with mock.patch.dict(
            os.environ,
            {"DEMO_SWITCH_CONTROLLER_EMAIL": self.controller.email},
        ):
            call_command("enable_demo_multprofile_switch")
        self.client.force_login(self.controller)

    def test_each_selected_profile_receives_its_own_home_template(self):
        expected = (
            (UserProfile.ADMINISTRATOR_GENERAL, "core/admin_home.html"),
            (UserProfile.AUXILIARY_ADMINISTRATIVE, "core/auxiliary_home.html"),
            (
                UserProfile.ADMINISTRATIVE_MANAGER,
                "core/administrative_manager_home.html",
            ),
            (UserProfile.CONTRACT_MANAGER, "core/contract_manager_home.html"),
            (UserProfile.FISCAL_TITULAR, "home.html"),
        )
        for profile, template in expected:
            with self.subTest(profile=profile):
                switched = self.client.post(
                    reverse("accounts:switch_profile"),
                    {"profile": profile},
                )
                self.assertRedirects(
                    switched,
                    reverse("home"),
                    fetch_redirect_response=False,
                )
                page = self.client.get(reverse("home"))
                self.assertTemplateUsed(page, template)
