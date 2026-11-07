from datetime import date
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from .forms import ReportFilterForm
from .models import WorkOrderAllocationStatus, WorkOrderStatus
from .reports import build_contract_report
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


class ContractReportTests(WorkOrderBase):
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
            work_order_id=self.order.pk, actor=self.owner, **execution_data()
        )
        self.invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                allocation=self.allocation,
                gross_value=Decimal("4000.00"),
                accepted_value=Decimal("4000.00"),
                status="Recebida da fonte",
            ),
        )
        self.payment = create_payment(
            invoice_id=self.invoice.pk,
            actor=self.owner,
            **payment_data(amount=Decimal("2500.00"), status="Pago conforme fonte"),
        )
        self.client = Client()

    def test_complete_report_reuses_financial_layer_and_all_records(self):
        report = build_contract_report(self.contract, {})
        self.assertEqual(report.financial_position, contract_financial_position(self.contract))
        self.assertEqual(report.commitments, (self.commitment,))
        self.assertEqual(report.work_orders, (self.order,))
        self.assertEqual(report.executions, (self.execution,))
        self.assertEqual(report.invoices, (self.invoice,))
        self.assertEqual(report.payments, (self.payment,))

    def test_financial_section_has_only_consolidated_totals(self):
        report = build_contract_report(
            self.contract, {"section": ReportFilterForm.Section.FINANCIAL}
        )
        self.assertEqual(report.financial_position.paid_value.value, Decimal("2500.00"))
        self.assertEqual(report.commitments, ())
        self.assertEqual(report.work_orders, ())
        self.assertEqual(report.invoices, ())

    def test_operational_and_billing_sections_are_separated(self):
        operational = build_contract_report(
            self.contract, {"section": ReportFilterForm.Section.OPERATIONAL}
        )
        billing = build_contract_report(
            self.contract, {"section": ReportFilterForm.Section.BILLING}
        )
        self.assertEqual(operational.work_orders, (self.order,))
        self.assertEqual(operational.invoices, ())
        self.assertEqual(billing.work_orders, ())
        self.assertEqual(billing.invoices, (self.invoice,))
        self.assertEqual(billing.payments, (self.payment,))

    def test_namespaced_status_filters_do_not_mix_entity_types(self):
        order_report = build_contract_report(
            self.contract, {"status": f"OS:{WorkOrderStatus.IN_PROGRESS}"}
        )
        invoice_report = build_contract_report(
            self.contract, {"status": "NF:Recebida da fonte"}
        )
        payment_report = build_contract_report(
            self.contract, {"status": "PAGAMENTO:Pago conforme fonte"}
        )
        self.assertEqual(order_report.work_orders, (self.order,))
        self.assertEqual(order_report.invoices, ())
        self.assertEqual(invoice_report.invoices, (self.invoice,))
        self.assertEqual(invoice_report.payments, (self.payment,))
        self.assertEqual(payment_report.payments, (self.payment,))

    def test_form_exposes_only_statuses_present_in_contract(self):
        form = ReportFilterForm(contract=self.contract)
        choices = dict(form.fields["status"].choices)
        self.assertIn(f"OS:{WorkOrderStatus.IN_PROGRESS}", choices)
        self.assertIn("NF:Recebida da fonte", choices)
        self.assertIn("PAGAMENTO:Pago conforme fonte", choices)
        self.assertNotIn(f"OS:{WorkOrderStatus.CANCELED}", choices)

    def test_report_is_protected_and_contract_scoped(self):
        url = reverse("contracts:report", args=[self.contract.pk])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_print_version_preserves_filters_and_hides_interactive_form(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("contracts:report", args=[self.contract.pk]),
            {"section": "billing", "competence": "09/2026", "print": "1"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Versão preparada para impressão")
        self.assertContains(response, "Notas Fiscais")
        self.assertNotContains(response, "Gerar relatório")
        self.assertContains(response, "Não constitui atesto")
        self.assertContains(response, "R$ 10.000,00")

    def test_print_button_opens_auto_print_version_in_new_tab(self):
        self.client.force_login(self.owner)
        url = reverse("contracts:report", args=[self.contract.pk])
        screen = self.client.get(url, {"section": "billing"})
        self.assertContains(screen, "Imprimir / Salvar PDF")
        self.assertContains(screen, 'target="_blank" rel="noopener"')
        self.assertContains(screen, "print=1")
        self.assertNotContains(screen, "data-auto-print")
        self.assertNotContains(screen, "report_print.js")
        printed = self.client.get(url, {"section": "billing", "print": "1"})
        self.assertContains(printed, "<span data-auto-print hidden></span>", html=False)
        self.assertContains(printed, "contracts/report_print.js")
        self.assertContains(printed, "@page { size: landscape; margin: 10mm; }")
        self.assertContains(printed, "Salvar como PDF")
        self.assertContains(printed, '<p class="helptext no-print">Versão preparada para impressão', html=False)
        self.assertNotContains(printed, "Imprimir / Salvar PDF")

    def test_invalid_filter_is_explained_without_server_error(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("contracts:report", args=[self.contract.pk]),
            {"start_date": "2026-10-01", "end_date": "2026-09-01"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data inicial não pode ser posterior")

    def test_annual_period_filter_uses_official_calendar_or_contract_dates(self):
        self.contract.validity_start = date(2026, 7, 1)
        self.contract.validity_end = date(2028, 6, 30)
        self.contract.save()
        civil = ReportFilterForm(
            {"annual_period": "civil:2"}, contract=self.contract
        )
        self.assertTrue(civil.is_valid(), civil.errors)
        self.assertEqual(civil.cleaned_data["start_date"], date(2027, 1, 1))
        self.assertEqual(civil.cleaned_data["end_date"], date(2027, 12, 31))
        contractual = ReportFilterForm(
            {"annual_period": "contratual:2"}, contract=self.contract
        )
        self.assertTrue(contractual.is_valid(), contractual.errors)
        self.assertEqual(contractual.cleaned_data["start_date"], date(2027, 7, 1))
        self.assertEqual(contractual.cleaned_data["end_date"], date(2028, 6, 30))

    def test_annual_period_cannot_be_combined_with_manual_dates(self):
        form = ReportFilterForm(
            {"annual_period": "civil:1", "start_date": "2026-07-01"},
            contract=self.contract,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("não ambos", form.non_field_errors()[0])

    def test_get_report_does_not_create_operational_records(self):
        before = (
            self.contract.commitments.count(),
            self.contract.work_orders.count(),
            self.contract.invoices.count(),
        )
        self.client.force_login(self.owner)
        self.client.get(reverse("contracts:report", args=[self.contract.pk]))
        after = (
            self.contract.commitments.count(),
            self.contract.work_orders.count(),
            self.contract.invoices.count(),
        )
        self.assertEqual(before, after)
