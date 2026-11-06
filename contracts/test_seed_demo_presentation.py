import os
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, User
from contracts.models import (
    BudgetCommitment,
    ContractItem,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderExecution,
    WorkOrderStatus,
)
from contracts.services import contract_financial_position, create_contract
from contracts.tests import VALID_PASSWORD, contract_data
from organizations.models import Organization

FISCAL_EMAIL = "admin@exemplo.com.br"


def seed(number="000885/2026", email=FISCAL_EMAIL):
    output = StringIO()
    with mock.patch.dict(os.environ, {"DEMO_CONTRACT_NUMBER": number, "DEMO_FISCAL_EMAIL": email}):
        call_command("seed_demo_presentation", stdout=output)
    return output.getvalue()


@override_settings(APP_ENVIRONMENT="demo")
class SeedDemoPresentationTests(TestCase):
    def setUp(self):
        today = timezone.localdate()
        self.fiscal = User.objects.create_user(
            email=FISCAL_EMAIL,
            full_name="Admin",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.create(name="SEMA"),
        )
        self.contract = create_contract(
            actor=self.fiscal,
            **contract_data(
                number="000885/2026",
                signature_date=today - timedelta(days=30),
                validity_start=today - timedelta(days=30),
                validity_end=today.replace(year=today.year + 4),
                original_value=Decimal("500000.00"),
            ),
        )

    def test_creates_complete_fictitious_package_within_limits(self):
        balance_before = contract_financial_position(self.contract).contract_balance.value
        seed()
        self.assertEqual(ContractItem.objects.filter(contract=self.contract).count(), 3)
        self.assertEqual(BudgetCommitment.objects.filter(contract=self.contract).count(), 2)
        orders = WorkOrder.objects.filter(contract=self.contract)
        self.assertEqual(orders.count(), 5)
        self.assertEqual(
            sorted(orders.values_list("status", flat=True)),
            sorted([
                WorkOrderStatus.COMPLETED, WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.IN_PROGRESS,
                WorkOrderStatus.SIGNED, WorkOrderStatus.DRAFT,
            ]),
        )
        self.assertEqual(WorkOrderExecution.objects.filter(work_order__contract=self.contract).count(), 2)
        self.assertEqual(Invoice.objects.filter(contract=self.contract).count(), 2)
        self.assertEqual(Payment.objects.filter(invoice__contract=self.contract).count(), 1)
        for model_qs in (ContractItem.objects.filter(contract=self.contract), orders):
            for obj in model_qs:
                self.assertTrue(
                    "[DEMO-APRESENTACAO]" in (getattr(obj, "source_reference", "") + getattr(obj, "notes", "") + getattr(obj, "description", ""))
                )
        position = contract_financial_position(self.contract)
        self.assertGreater(position.contract_balance.value, Decimal("0"))
        self.assertLessEqual(position.committed_value.value, balance_before)

    def test_is_idempotent(self):
        seed()
        self.assertIn("já existem", seed())
        self.assertEqual(WorkOrder.objects.filter(contract=self.contract).count(), 5)

    def test_dashboard_shows_alerts_for_fiscal(self):
        seed()
        self.client.force_login(self.fiscal)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "DEMO-OS-03")
        self.assertContains(response, "venceu")

    def test_refuses_contract_of_another_fiscal(self):
        other = User.objects.create_user(
            email="outro@exemplo.com.br", full_name="Outro", password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE, organization=Organization.objects.get(name="SEMA"),
        )
        with self.assertRaises(CommandError):
            seed(email=other.email)
        self.assertFalse(ContractItem.objects.filter(contract=self.contract).exists())

    @override_settings(APP_ENVIRONMENT="production")
    def test_refuses_outside_demo(self):
        with self.assertRaises(CommandError):
            seed()
