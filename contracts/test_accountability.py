from datetime import date
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from .accountability import build_accountability_snapshot
from .models import WorkOrderAllocationStatus, WorkOrderStatus
from .services import (
    contract_financial_position,
    create_budget_commitment,
    create_invoice,
    create_payment,
    create_work_order_allocation,
    create_work_order_execution,
)
from .test_commitments import commitment_data
from .test_executions import execution_data
from .test_invoices import invoice_data
from .test_payments import payment_data
from .test_work_orders import WorkOrderBase


class AccountabilityTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("12000.00")),
        )
        self.allocation = create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            commitment=self.commitment,
            amount=Decimal("10000.00"),
            allocation_date=date(2026, 9, 28),
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        self.execution = create_work_order_execution(
            work_order_id=self.order.pk,
            actor=self.owner,
            **execution_data(),
        )
        self.invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                allocation=self.allocation,
                gross_value=Decimal("4000.00"),
                accepted_value=Decimal("4000.00"),
            ),
        )
        self.payment = create_payment(
            invoice_id=self.invoice.pk,
            actor=self.owner,
            **payment_data(amount=Decimal("2500.00")),
        )
        self.client = Client()

    def test_snapshot_reuses_consolidated_financial_position(self):
        snapshot = build_accountability_snapshot(self.contract, {})
        expected = contract_financial_position(self.contract)
        self.assertEqual(snapshot.financial_position, expected)
        self.assertEqual(snapshot.financial_position.paid_value.value, Decimal("2500.00"))

    def test_snapshot_exposes_traceable_records_without_writing(self):
        counts_before = tuple(
            manager.count()
            for manager in (
                self.contract.commitments,
                self.contract.work_orders,
                self.contract.invoices,
            )
        )
        snapshot = build_accountability_snapshot(self.contract, {})
        self.assertEqual(snapshot.commitments, (self.commitment,))
        self.assertEqual(snapshot.work_orders, (self.order,))
        self.assertEqual(snapshot.executions, (self.execution,))
        self.assertEqual(snapshot.invoices, (self.invoice,))
        self.assertEqual(snapshot.payments, (self.payment,))
        self.assertEqual(
            counts_before,
            tuple(
                manager.count()
                for manager in (
                    self.contract.commitments,
                    self.contract.work_orders,
                    self.contract.invoices,
                )
            ),
        )

    def test_competence_filters_only_records_that_have_competence(self):
        snapshot = build_accountability_snapshot(
            self.contract, {"competence": "10/2026"}
        )
        self.assertEqual(snapshot.commitments, (self.commitment,))
        self.assertEqual(snapshot.work_orders, (self.order,))
        self.assertEqual(snapshot.executions, ())
        self.assertEqual(snapshot.invoices, ())
        self.assertEqual(snapshot.payments, ())

    def test_period_uses_each_records_own_date(self):
        snapshot = build_accountability_snapshot(
            self.contract,
            {"start_date": date(2026, 9, 30), "end_date": date(2026, 9, 30)},
        )
        self.assertEqual(snapshot.commitments, ())
        self.assertEqual(snapshot.work_orders, ())
        self.assertEqual(snapshot.executions, ())
        self.assertEqual(snapshot.invoices, ())
        self.assertEqual(snapshot.payments, (self.payment,))

    def test_combined_commitment_work_order_and_invoice_filters_remain_scoped(self):
        snapshot = build_accountability_snapshot(
            self.contract,
            {
                "commitment": self.commitment,
                "work_order": self.order,
                "invoice": self.invoice,
            },
        )
        self.assertEqual(snapshot.commitments, (self.commitment,))
        self.assertEqual(snapshot.work_orders, (self.order,))
        self.assertEqual(snapshot.invoices, (self.invoice,))
        self.assertEqual(snapshot.payments, (self.payment,))

    def test_page_is_protected_and_other_fiscal_cannot_access_contract(self):
        url = reverse("contracts:accountability", args=[self.contract.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_page_renders_totals_drill_down_and_document_warning(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("contracts:accountability", args=[self.contract.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Posição consolidada")
        self.assertContains(response, "Contrato 001/2099")
        self.assertContains(response, "Atesto, RAER e Termo de Homologação")
        self.assertContains(response, reverse(
            "contracts:invoice_detail",
            args=[self.contract.pk, self.order.pk, self.invoice.pk],
        ))

    def test_invalid_period_is_explained_and_does_not_crash(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("contracts:accountability", args=[self.contract.pk]),
            {"start_date": "2026-10-01", "end_date": "2026-09-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data inicial não pode ser posterior")
