from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from .models import Invoice, InvoiceEvent, WorkOrderStatus
from .services import (
    cancel_work_order,
    contract_financial_position,
    create_contract,
    create_contract_item,
    create_invoice,
    create_work_order,
    possible_duplicate_invoice_ids,
    update_invoice,
    update_work_order,
    work_order_invoice_position,
)
from .test_items import item_data
from .test_work_orders import WorkOrderBase, work_order_data
from .tests import contract_data


def invoice_data(contract, **overrides):
    data = {
        "item": None,
        "allocation": None,
        "number": "NF-001",
        "series": "A",
        "supplier_name": contract.supplier_name,
        "supplier_tax_id": contract.supplier_tax_id,
        "issue_date": date(2026, 9, 29),
        "competence": "09/2026",
        "gross_value": Decimal("6000.00"),
        "deduction_value": Decimal("0.00"),
        "accepted_value": Decimal("6000.00"),
        "process_number": "PROCESSO-NF-001",
        "status": "Recebida",
        "document_reference": "Documento fiscal 001",
        "document_hash": "",
        "notes": "",
    }
    data.update(overrides)
    return data


class InvoiceTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.client = Client()

    def create_invoice(self, **overrides):
        return create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(self.contract, **overrides),
        )

    def test_create_keeps_values_distinct_and_audits_source_fields(self):
        invoice = self.create_invoice(
            gross_value=Decimal("6000.00"),
            deduction_value=Decimal("500.00"),
            accepted_value=Decimal("5200.00"),
        )
        self.assertEqual(invoice.gross_value, Decimal("6000.00"))
        self.assertEqual(invoice.deduction_value, Decimal("500.00"))
        self.assertEqual(invoice.accepted_value, Decimal("5200.00"))
        self.assertEqual(invoice.contract, self.contract)
        event = InvoiceEvent.objects.get(invoice=invoice)
        self.assertEqual(event.event_type, InvoiceEvent.EventType.CREATED)
        self.assertEqual(event.details["atual"]["valor_aceito"], "5200.00")

    def test_formula_between_gross_deduction_and_accepted_is_not_invented(self):
        invoice = self.create_invoice(
            gross_value=Decimal("6000.00"),
            deduction_value=Decimal("500.00"),
            accepted_value=Decimal("5000.00"),
        )
        self.assertNotEqual(
            invoice.accepted_value, invoice.gross_value - invoice.deduction_value
        )
        self.assertFalse(Invoice._meta.get_field("status").choices)

    def test_values_competence_and_hash_are_validated(self):
        with self.assertRaises(ValidationError):
            self.create_invoice(gross_value=Decimal("0.00"))
        with self.assertRaisesMessage(ValidationError, "glosa"):
            self.create_invoice(deduction_value=Decimal("6000.01"))
        with self.assertRaisesMessage(ValidationError, "valor aceito"):
            self.create_invoice(accepted_value=Decimal("6000.01"))
        with self.assertRaisesMessage(ValidationError, "MM/AAAA"):
            self.create_invoice(competence="13/2026")
        with self.assertRaisesMessage(ValidationError, "SHA-256"):
            self.create_invoice(document_hash="hash-invalido")

    def test_supplier_and_tax_id_must_match_contract(self):
        with self.assertRaisesMessage(ValidationError, "fornecedor"):
            self.create_invoice(supplier_name="Fornecedor diferente")
        with self.assertRaisesMessage(ValidationError, "CNPJ/CPF"):
            self.create_invoice(supplier_tax_id="11111111000111")

    def test_item_and_work_order_must_share_contract_and_correspond(self):
        second_contract = create_contract(
            actor=self.owner,
            **contract_data(number="038/2026", process_number="PROCESSO-038"),
        )
        foreign_item = create_contract_item(
            contract_id=second_contract.pk,
            actor=self.owner,
            **item_data(number="ITEM-FORA"),
        )
        with self.assertRaisesMessage(ValidationError, "mesmo contrato"):
            self.create_invoice(item=foreign_item)
        other_item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(number="ITEM-2"),
        )
        with self.assertRaisesMessage(ValidationError, "corresponder ao item da OS"):
            self.create_invoice(item=other_item)

    def test_partial_invoices_reach_order_value_and_third_is_blocked(self):
        first = self.create_invoice(gross_value=Decimal("6000.00"))
        second = self.create_invoice(
            number="NF-002", gross_value=Decimal("4000.00"),
            accepted_value=Decimal("4000.00"),
        )
        position = work_order_invoice_position(self.order)
        self.assertEqual(position.invoiced_gross_value.value, Decimal("10000.00"))
        self.assertEqual(position.billable_balance.value, Decimal("0.00"))
        self.assertEqual(len(position.invoiced_gross_value.evidence), 2)
        with self.assertRaisesMessage(ValidationError, "ultrapassa"):
            self.create_invoice(
                number="NF-003", gross_value=Decimal("10.00"),
                accepted_value=Decimal("10.00"),
            )
        self.assertEqual(Invoice.objects.filter(pk__in=(first.pk, second.pk)).count(), 2)

    def test_context_and_hash_duplicates_are_alerts_not_silent_confirmation(self):
        digest = "a" * 64
        first = self.create_invoice(
            document_hash=digest, gross_value=Decimal("3000.00"),
            accepted_value=Decimal("3000.00"),
        )
        same_context = self.create_invoice(
            document_hash="", gross_value=Decimal("3000.00"),
            accepted_value=Decimal("3000.00"),
        )
        by_hash = self.create_invoice(
            number="NF-OUTRA", series="B", document_hash=digest,
            gross_value=Decimal("1000.00"), accepted_value=Decimal("1000.00"),
        )
        self.assertIn(first.pk, possible_duplicate_invoice_ids(same_context))
        self.assertIn(first.pk, possible_duplicate_invoice_ids(by_hash))
        self.assertIn(first.pk, by_hash.events.first().details["possiveis_duplicatas"])

    def test_update_is_audited_and_cannot_overrun_order(self):
        invoice = self.create_invoice()
        updated = update_invoice(
            invoice_id=invoice.pk,
            actor=self.owner,
            **invoice_data(
                self.contract, gross_value=Decimal("5000.00"),
                accepted_value=Decimal("4800.00"), status="Em análise",
            ),
        )
        self.assertEqual(updated.status, "Em análise")
        self.assertEqual(updated.events.first().event_type, InvoiceEvent.EventType.UPDATED)
        self.create_invoice(
            number="NF-002", gross_value=Decimal("5000.00"),
            accepted_value=Decimal("5000.00"),
        )
        with self.assertRaisesMessage(ValidationError, "ultrapassa"):
            update_invoice(
                invoice_id=updated.pk,
                actor=self.owner,
                **invoice_data(
                    self.contract, gross_value=Decimal("5000.01"),
                    accepted_value=Decimal("5000.01"),
                ),
            )

    def test_order_cannot_be_reduced_or_canceled_with_invoice(self):
        self.create_invoice()
        with self.assertRaisesMessage(ValidationError, "total bruto já faturado"):
            update_work_order(
                work_order_id=self.order.pk, actor=self.owner,
                **work_order_data(
                    self.item, number=self.order.number, hours=Decimal("20.0000"),
                    status=WorkOrderStatus.IN_PROGRESS,
                ),
            )
        with self.assertRaisesMessage(ValidationError, "tratamento explícito"):
            cancel_work_order(
                work_order_id=self.order.pk, actor=self.owner,
                reason="Cancelamento que exige tratamento da NF",
            )

    def test_contract_position_exposes_gross_invoice_evidence(self):
        invoice = self.create_invoice()
        position = contract_financial_position(self.contract)
        self.assertEqual(position.invoiced_gross_value.value, Decimal("6000.00"))
        self.assertEqual(position.invoiced_gross_value.evidence[0].source_id, str(invoice.pk))
        self.assertNotEqual(position.executed_value.value, position.invoiced_gross_value.value)

    def test_other_fiscal_is_hidden_and_administrator_is_read_only(self):
        invoice = self.create_invoice()
        with self.assertRaises(Invoice.DoesNotExist):
            update_invoice(
                invoice_id=invoice.pk, actor=self.other,
                **invoice_data(self.contract),
            )
        self.client.force_login(self.other)
        url = reverse(
            "contracts:invoice_detail",
            args=[self.contract.pk, self.order.pk, invoice.pk],
        )
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_invoice_add")).status_code, 403
        )

    def test_web_form_localizes_money_and_shows_objective_limit(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:invoice_create", args=[self.contract.pk, self.order.pk]),
            {
                "item": self.item.pk, "allocation": "", "number": "NF-WEB",
                "series": "A", "supplier_name": self.contract.supplier_name,
                "supplier_tax_id": self.contract.supplier_tax_id,
                "issue_date": "2026-09-29", "competence": "09/2026",
                "gross_value": "6.000,00", "deduction_value": "500,00",
                "accepted_value": "5.200,00", "process_number": "PROC-WEB",
                "status": "Recebida", "document_reference": "Referência",
                "document_hash": "", "notes": "",
            },
        )
        invoice = Invoice.objects.get(number="NF-WEB")
        self.assertRedirects(
            response,
            reverse(
                "contracts:invoice_detail",
                args=[self.contract.pk, self.order.pk, invoice.pk],
            ),
        )
        detail = self.client.get(response.url)
        self.assertContains(detail, "Total após inclusão")
        self.assertContains(detail, "6.000,00")
        self.assertContains(detail, "Nenhum pagamento é inferido")

    def test_no_delete_route_and_permissions_are_least_privilege(self):
        self.assertTrue(self.owner.has_perm("contracts.add_invoice"))
        self.assertTrue(self.owner.has_perm("contracts.change_invoice"))
        self.assertTrue(self.manager.has_perm("contracts.view_invoice"))
        self.assertFalse(self.manager.has_perm("contracts.add_invoice"))
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("invoice_delete", route_names)
