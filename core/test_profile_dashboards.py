"""Painéis independentes e gerenciais dos perfis (Sprints 58 e 59)."""

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
    ContractItem,
    ContractItemUnit,
    ContractManagementCategory,
    IntelligenceReviewStatus,
    WorkOrder,
    WorkOrderStatus,
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
        ContractAccess.objects.create(
            contract=cls.contract_b,
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
        item_a = cls._item(cls.contract_a)
        item_b = cls._item(cls.contract_b)
        archived_item = cls._item(cls.archived_contract)
        cls.open_order = cls._work_order(
            cls.contract_a,
            item_a,
            "OS-ABERTA-ATRASADA/2026",
            WorkOrderStatus.OPEN,
            deadline=date(2026, 11, 18),
            hours=Decimal("40.0000"),
        )
        cls.signed_order = cls._work_order(
            cls.contract_b,
            item_b,
            "OS-ASSINADA/2026",
            WorkOrderStatus.SIGNED,
            deadline=date(2027, 1, 31),
            hours=Decimal("20.0000"),
        )
        cls.completed_order = cls._work_order(
            cls.contract_a,
            item_a,
            "OS-CONCLUIDA/2026",
            WorkOrderStatus.COMPLETED,
            deadline=date(2026, 10, 31),
            hours=Decimal("10.0000"),
            completion_date=date(2026, 10, 30),
        )
        cls.archived_order = cls._work_order(
            cls.archived_contract,
            archived_item,
            "OS-ARQUIVADA/2026",
            WorkOrderStatus.OPEN,
            deadline=date(2026, 11, 1),
            hours=Decimal("15.0000"),
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

    @classmethod
    def _item(cls, contract):
        return ContractItem.objects.create(
            contract=contract,
            number="1",
            description="Hora técnica fictícia",
            category="Serviço",
            unit=ContractItemUnit.HOUR,
            contracted_quantity=Decimal("500.0000"),
            unit_value=Decimal("250.00"),
            created_by=cls.fiscal,
        )

    @classmethod
    def _work_order(
        cls,
        contract,
        item,
        number,
        status,
        *,
        deadline,
        hours,
        completion_date=None,
    ):
        return WorkOrder.objects.create(
            contract=contract,
            item=item,
            number=number,
            description="Execução exclusivamente fictícia",
            hours=hours,
            unit_value=item.unit_value,
            unit_name=item.unit_display,
            responsible="Responsável fictício",
            opening_date=date(2026, 1, 10),
            deadline=deadline,
            completion_date=completion_date,
            status=status,
            process_number=f"PROC-{number}",
            created_by=cls.fiscal,
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

    @mock.patch("core.profile_dashboards.timezone.localdate", return_value=date(2026, 11, 19))
    def test_auxiliary_has_open_and_overdue_orders_without_private_content(
        self, _localdate
    ):
        self.client.force_login(self.auxiliary)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/auxiliary_home.html")
        self.assertContains(page, "Acompanhamento administrativo das OS")
        self.assertContains(page, self.open_order.number)
        self.assertContains(page, self.signed_order.number)
        self.assertNotContains(page, self.completed_order.number)
        self.assertNotContains(page, self.archived_order.number)
        self.assertNotContains(page, self.archived_contract.number)
        self.assertContains(page, "OS em atraso")
        self.assertContains(page, "40,00 h")
        self.assertContains(page, "R$&nbsp;10.000,00", html=False)
        self.assertNotContains(page, "Contrato fictício catalogado")
        self.assertNotContains(
            page,
            reverse(
                "contracts:work_order_detail",
                args=[self.contract_a.pk, self.open_order.pk],
            ),
        )
        self.assertNotContains(page, reverse("contracts:executive_dashboard"))

        notifications = build_notifications(self.auxiliary)
        self.assertGreaterEqual(notifications["count"], 1)
        self.assertTrue(
            any(
                item["hint"] == "Acompanhar OS em atraso"
                and item["url"].endswith("#aux-os")
                for item in notifications["items"]
            )
        )
        self.assertFalse(
            any("valor" in item["title"].lower() for item in notifications["items"])
        )

        selected = self.client.get(reverse("home"), {"contract": self.contract_b.pk})
        self.assertEqual(selected.status_code, 200)
        self.assertNotContains(selected, self.open_order.number)
        self.assertContains(selected, self.signed_order.number)
        forbidden = self.client.get(
            reverse("home"), {"contract": self.archived_contract.pk}
        )
        self.assertEqual(forbidden.status_code, 404)

    def test_administrative_manager_has_consolidated_classified_portfolio(self):
        self.client.force_login(self.administrative_manager)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/administrative_manager_home.html")
        self.assertContains(page, "Dashboard gerencial dos contratos")
        self.assertContains(page, "Sistema")
        self.assertContains(page, "Equipamento")
        self.assertContains(page, self.contract_a.number)
        self.assertContains(page, self.contract_b.number)
        self.assertNotContains(page, self.archived_contract.number)
        self.assertContains(page, "R$&nbsp;200.000,00", html=False)
        self.assertContains(page, reverse("contracts:executive_dashboard"))
        self.assertContains(
            page, reverse("contracts:administrative_portfolio_report")
        )
        self.assertContains(page, "Gráfico financeiro")
        self.assertContains(page, "Situação das OS")

        selected = self.client.get(reverse("home"), {"contract": self.contract_b.pk})
        self.assertEqual(
            selected.context["administrative_dashboard"].get("scope_label"),
            f"Contrato {self.contract_b.number}",
        )
        self.assertEqual(
            selected.context["administrative_dashboard"]["portfolio"].current_value,
            Decimal("100000.00"),
        )

    def test_administrative_manager_can_emit_general_and_individual_report(self):
        self.client.force_login(self.administrative_manager)
        report_url = reverse("contracts:administrative_portfolio_report")
        general = self.client.get(report_url)
        self.assertEqual(general.status_code, 200)
        self.assertContains(general, "Relatório gerencial dos contratos")
        self.assertContains(general, "Todos os contratos")
        self.assertContains(general, self.contract_a.number)
        self.assertContains(general, self.contract_b.number)

        individual = self.client.get(report_url, {"contract": self.contract_a.pk})
        self.assertEqual(individual.status_code, 200)
        self.assertEqual(
            individual.context["administrative_dashboard"]["portfolio"].contract_count,
            1,
        )
        printed = self.client.get(
            report_url, {"contract": self.contract_a.pk, "print": "1"}
        )
        self.assertContains(printed, "data-auto-print")

        self.client.force_login(self.auxiliary)
        self.assertEqual(self.client.get(report_url).status_code, 403)

    def test_contract_manager_selects_among_linked_contracts_and_reports(self):
        self.client.force_login(self.contract_manager)
        page = self.client.get(reverse("home"))
        self.assertTemplateUsed(page, "core/contract_manager_home.html")
        self.assertContains(page, "Painel de acompanhamento individual")
        self.assertContains(page, "Gráfico financeiro")
        self.assertContains(page, self.contract_a.number)
        self.assertContains(page, self.contract_b.number)
        self.assertContains(page, reverse("contracts:report", args=[self.contract_a.pk]))
        self.assertContains(page, "Somente leitura")
        selected = self.client.get(reverse("home"), {"contract": self.contract_b.pk})
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(
            selected.context["contract_manager_dashboard"]["selected_contract"],
            self.contract_b,
        )
        forbidden = self.client.get(
            reverse("home"), {"contract": self.archived_contract.pk}
        )
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
