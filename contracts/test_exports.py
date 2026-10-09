import csv
import io
from datetime import date
from decimal import Decimal

from django.db import DatabaseError, transaction
from django.test import Client
from django.urls import reverse

from .models import (
    CommitmentMovement,
    CsvExportEvent,
    WorkOrderAllocationStatus,
    WorkOrderStatus,
)
from .services import (
    create_budget_commitment,
    create_commitment_movement,
    create_invoice,
    create_payment,
    create_work_order_allocation,
    create_work_order_execution,
    share_contract_read_only,
)
from .test_commitments import commitment_data, movement_data
from .test_executions import execution_data
from .test_invoices import invoice_data
from .test_payments import payment_data
from .test_work_orders import WorkOrderBase


class ContractCsvExportTests(WorkOrderBase):
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
        self.url = reverse("contracts:export_csv", args=[self.contract.pk])

    def rows(self, response):
        content = response.content.decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(content), delimiter=";"))

    def test_export_is_utf8_excel_friendly_and_reuses_financial_totals(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content[:3], b"\xef\xbb\xbf")
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        rows = self.rows(response)
        self.assertIn("fechamento_ano_civil", rows[0])
        self.assertIn("ano_contratual", rows[0])
        summaries = {
            row["indicador"]: row["valor_brl"]
            for row in rows if row["tipo_registro"] == "RESUMO"
        }
        self.assertEqual(summaries["Empenhado ativo"], "12000,00")
        self.assertEqual(summaries["Comprometido"], "10000,00")
        self.assertEqual(summaries["Pago registrado"], "2500,00")
        self.assertEqual(
            {row["tipo_registro"] for row in rows},
            {"RESUMO", "EMPENHO", "ORDEM_SERVICO", "EXECUCAO", "NOTA_FISCAL", "PAGAMENTO"},
        )
        order_row = next(row for row in rows if row["tipo_registro"] == "ORDEM_SERVICO")
        self.assertEqual(order_row["fechamento_ano_civil"], "Fechamento 2026")
        self.assertEqual(order_row["ano_contratual"], "Ano contratual 1")

    def test_export_preserves_report_section_and_status_filters(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            self.url,
            {"section": "billing", "status": "NF:Recebida da fonte"},
        )
        rows = self.rows(response)
        types = {row["tipo_registro"] for row in rows}
        self.assertEqual(types, {"RESUMO", "NOTA_FISCAL", "PAGAMENTO"})
        event = CsvExportEvent.objects.latest("pk")
        self.assertEqual(event.details["filtros"]["section"], "billing")
        self.assertEqual(event.details["filtros"]["status"], "NF:Recebida da fonte")

    def test_export_includes_reversal_and_official_document_reference(self):
        create_commitment_movement(
            commitment_id=self.commitment.pk,
            actor=self.owner,
            **movement_data(
                movement_type=CommitmentMovement.Type.REVERSAL,
                movement_date=date(2026, 12, 31),
                amount=Decimal("2000.00"),
                document_reference="DEMO-DOC-2026/ESTORNO-001",
            ),
        )
        self.client.force_login(self.owner)

        rows = self.rows(self.client.get(self.url))
        reversal = next(
            row for row in rows if row["tipo_registro"] == "MOVIMENTO_EMPENHO"
        )
        self.assertEqual(reversal["status"], "Estorno do saldo do exercício")
        self.assertEqual(reversal["valor_brl"], "2000,00")
        self.assertIn("DEMO-DOC-2026/ESTORNO-001", reversal["descricao"])

    def test_export_audits_file_filters_and_exact_row_count(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url, {"competence": "09/2026"})
        event = CsvExportEvent.objects.get()
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.contract, self.contract)
        self.assertEqual(event.details["formato"], "CSV UTF-8")
        self.assertEqual(event.details["delimitador"], ";")
        self.assertEqual(event.details["linhas"], len(self.rows(response)))
        self.assertEqual(event.details["filtros"]["competence"], "09/2026")

    def test_anonymous_foreign_and_read_only_users_cannot_export(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        share_contract_read_only(
            contract_id=self.contract.pk, actor=self.owner, email=self.other.email
        )
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(CsvExportEvent.objects.count(), 0)

    def test_administrator_with_global_contract_permission_can_export(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(CsvExportEvent.objects.get().actor, self.manager)

    def test_invalid_filter_fails_closed_without_audit_event(self):
        self.client.force_login(self.owner)
        response = self.client.get(
            self.url, {"start_date": "2026-10-01", "end_date": "2026-09-01"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(CsvExportEvent.objects.count(), 0)

    def test_text_is_protected_against_spreadsheet_formula_injection(self):
        self.create_work_order(
            number="OS-CSV-002", hours=Decimal("1.0000"),
            description="=HYPERLINK(\"https://invalid.local\")",
        )
        self.client.force_login(self.owner)
        rows = self.rows(self.client.get(self.url))
        row = next(item for item in rows if item["identificador"] == "OS-CSV-002")
        self.assertTrue(row["descricao"].startswith("'="))

    def test_export_does_not_change_operational_records(self):
        before = (
            self.contract.commitments.count(), self.contract.work_orders.count(),
            self.contract.invoices.count(), self.invoice.payments.count(),
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        after = (
            self.contract.commitments.count(), self.contract.work_orders.count(),
            self.contract.invoices.count(), self.invoice.payments.count(),
        )
        self.assertEqual(before, after)

    def test_export_event_is_immutable_in_postgresql(self):
        self.client.force_login(self.owner)
        self.client.get(self.url)
        event = CsvExportEvent.objects.get()
        with self.assertRaises(DatabaseError), transaction.atomic():
            CsvExportEvent.objects.filter(pk=event.pk).update(details={"violado": True})
        with self.assertRaises(DatabaseError), transaction.atomic():
            CsvExportEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(CsvExportEvent.objects.filter(pk=event.pk).exists())

    def test_authorized_pages_show_export_and_read_only_pages_do_not(self):
        self.client.force_login(self.owner)
        for name in ("contracts:accountability", "contracts:report"):
            response = self.client.get(reverse(name, args=[self.contract.pk]))
            self.assertContains(response, self.url)
        share_contract_read_only(
            contract_id=self.contract.pk, actor=self.owner, email=self.other.email
        )
        self.client.force_login(self.other)
        for name in ("contracts:accountability", "contracts:report"):
            response = self.client.get(reverse(name, args=[self.contract.pk]))
            self.assertNotContains(response, self.url)
