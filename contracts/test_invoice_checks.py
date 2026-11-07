from decimal import Decimal

from django.urls import reverse

from .invoice_checks import CheckStatus, OverallStatus
from .models import WorkOrderAllocationStatus, WorkOrderStatus
from .services import (
    create_budget_commitment,
    create_invoice,
    create_work_order_allocation,
    invoice_check_report,
)
from .test_commitments import commitment_data
from .test_invoices import invoice_data
from .test_work_orders import WorkOrderBase


class InvoiceCheckTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )

    def create_invoice(self, **overrides):
        data = invoice_data(self.contract, item=self.item)
        data.update(overrides)
        return create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **data,
        )

    def check_by_code(self, report, code):
        return next(check for check in report.checks if check.code == code)

    def test_complete_consistent_invoice_is_conferred_with_nine_explained_checks(self):
        report = invoice_check_report(self.create_invoice())
        self.assertEqual(report.overall_status, OverallStatus.CONFERRED)
        self.assertEqual(len(report.checks), 9)
        self.assertTrue(all(check.message for check in report.checks))
        self.assertEqual(
            self.check_by_code(report, "EMPENHO_RATEIO").status,
            CheckStatus.NOT_APPLICABLE,
        )

    def test_missing_item_is_a_pending_fact_not_an_invented_match(self):
        invoice = self.create_invoice(item=None)
        report = invoice_check_report(invoice)
        self.assertEqual(report.overall_status, OverallStatus.PENDING)
        self.assertEqual(self.check_by_code(report, "ITEM").actual, "Não informado")

    def test_active_allocation_requires_explicit_invoice_link(self):
        create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            commitment=self.commitment,
            amount=Decimal("5000.00"),
            allocation_date=self.order.opening_date,
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        report = invoice_check_report(self.create_invoice())
        self.assertEqual(report.overall_status, OverallStatus.PENDING)
        self.assertEqual(
            self.check_by_code(report, "EMPENHO_RATEIO").status,
            CheckStatus.PENDING,
        )

    def test_possible_duplicate_has_specific_overall_result(self):
        first = self.create_invoice(
            gross_value=Decimal("3000.00"), accepted_value=Decimal("3000.00")
        )
        second = self.create_invoice(
            gross_value=Decimal("3000.00"), accepted_value=Decimal("3000.00")
        )
        report = invoice_check_report(second)
        duplicate = self.check_by_code(report, "DUPLICIDADE")
        self.assertEqual(report.overall_status, OverallStatus.POSSIBLE_DUPLICATE)
        self.assertEqual(duplicate.related_ids, (first.pk,))

    def test_canceled_order_blocks_report_even_for_preserved_invoice(self):
        invoice = self.create_invoice()
        type(self.order).objects.filter(pk=self.order.pk).update(
            status=WorkOrderStatus.CANCELED
        )
        invoice.refresh_from_db()
        report = invoice_check_report(invoice)
        self.assertEqual(report.overall_status, OverallStatus.BLOCKED)
        self.assertEqual(
            self.check_by_code(report, "ORDEM_SERVICO").status,
            CheckStatus.BLOCKED,
        )

    def test_supplier_divergence_is_explained_without_mutating_invoice(self):
        invoice = self.create_invoice()
        type(invoice).objects.filter(pk=invoice.pk).update(
            supplier_name="Fornecedor divergente"
        )
        invoice.refresh_from_db()
        report = invoice_check_report(invoice)
        self.assertEqual(report.overall_status, OverallStatus.DIVERGENCE)
        supplier = self.check_by_code(report, "FORNECEDOR")
        self.assertEqual(supplier.expected, self.contract.supplier_name)
        self.assertEqual(supplier.actual, "Fornecedor divergente")

    def test_value_check_does_not_infer_acceptance_formula_and_is_deterministic(self):
        invoice = self.create_invoice(
            gross_value=Decimal("6000.00"),
            deduction_value=Decimal("500.00"),
            accepted_value=Decimal("5000.00"),
        )
        first = invoice_check_report(invoice)
        second = invoice_check_report(invoice)
        value_check = self.check_by_code(first, "VALOR")
        self.assertEqual(first, second)
        self.assertEqual(value_check.status, CheckStatus.OK)
        self.assertIn("nenhuma fórmula", value_check.message)

    def test_detail_page_displays_general_and_individual_results(self):
        invoice = self.create_invoice()
        self.client.force_login(self.owner)
        response = self.client.get(reverse(
            "contracts:invoice_detail",
            args=[self.contract.pk, self.order.pk, invoice.pk],
        ))
        self.assertContains(response, "Conferência determinística")
        self.assertContains(response, "Conferida")  # texto legível (Sprint 16); antes exibia o código CONFERIDA
        self.assertContains(response, "Saldo faturável")
        self.assertContains(response, "Não usa IA")
