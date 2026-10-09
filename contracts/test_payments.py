from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse

from .models import Payment, PaymentEvent, WorkOrderStatus
from .services import (
    contract_financial_position,
    create_invoice,
    create_payment,
    invoice_payment_position,
    update_invoice,
    update_payment,
)
from .test_invoices import invoice_data
from .test_work_orders import WorkOrderBase


def payment_data(**overrides):
    data = {
        "amount": Decimal("6000.00"),
        "payment_date": date(2026, 9, 30),
        "competence": "09/2026",
        "status": "Pago conforme fonte",
        "process_number": "PROCESSO-PAG-001",
        "attestation_reference": "Atesto 001",
        "raer_reference": "RAER 001",
        "homologation_reference": "Termo de Homologação 001",
        "evidence_reference": "Comprovante 001",
        "notes": "",
    }
    data.update(overrides)
    return data


class PaymentTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                gross_value=Decimal("10000.00"),
                accepted_value=Decimal("10000.00"),
            ),
        )
        self.client = Client()

    def create_payment(self, **overrides):
        return create_payment(
            invoice_id=self.invoice.pk,
            actor=self.owner,
            **payment_data(**overrides),
        )

    def test_create_preserves_source_fields_and_audits(self):
        payment = self.create_payment(amount=Decimal("2500.00"))
        self.assertEqual(payment.invoice, self.invoice)
        self.assertEqual(payment.attestation_reference, "Atesto 001")
        self.assertEqual(payment.raer_reference, "RAER 001")
        self.assertEqual(payment.homologation_reference, "Termo de Homologação 001")
        event = PaymentEvent.objects.get(payment=payment)
        self.assertEqual(event.event_type, PaymentEvent.EventType.CREATED)
        self.assertEqual(event.details["atual"]["valor"], "2500.00")

    def test_three_document_references_and_competence_are_required_or_validated(self):
        for field in (
            "attestation_reference",
            "raer_reference",
            "homologation_reference",
        ):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.create_payment(**{field: ""})
        with self.assertRaisesMessage(ValidationError, "MM/AAAA"):
            self.create_payment(competence="13/2026")

    def test_partial_payments_reach_limit_and_excess_is_blocked(self):
        self.create_payment(amount=Decimal("6000.00"))
        self.create_payment(
            amount=Decimal("4000.00"), process_number="PROCESSO-PAG-002"
        )
        position = invoice_payment_position(self.invoice)
        self.assertEqual(position.paid_total.value, Decimal("10000.00"))
        self.assertEqual(position.payment_balance.value, Decimal("0.00"))
        with self.assertRaisesMessage(ValidationError, "ultrapassa"):
            self.create_payment(amount=Decimal("0.01"))

    def test_provisional_limit_is_lower_of_gross_and_accepted(self):
        self.invoice.accepted_value = Decimal("8000.00")
        self.invoice.save()
        self.create_payment(amount=Decimal("8000.00"))
        position = invoice_payment_position(self.invoice)
        self.assertEqual(position.provisional_payable_limit.value, Decimal("8000.00"))
        self.assertFalse(Payment._meta.get_field("status").choices)
        with self.assertRaisesMessage(ValidationError, "ultrapassa"):
            self.create_payment(amount=Decimal("0.01"))

    def test_update_is_audited_and_invoice_cannot_drop_below_paid_total(self):
        payment = self.create_payment(amount=Decimal("7000.00"))
        updated = update_payment(
            payment_id=payment.pk,
            actor=self.owner,
            **payment_data(amount=Decimal("6500.00"), status="Liquidado na fonte"),
        )
        self.assertEqual(updated.status, "Liquidado na fonte")
        event = updated.events.first()
        self.assertEqual(event.event_type, PaymentEvent.EventType.UPDATED)
        self.assertEqual(event.details["anterior"]["valor"], "7000.00")
        with self.assertRaisesMessage(ValidationError, "ultrapassa"):
            update_invoice(
                invoice_id=self.invoice.pk,
                actor=self.owner,
                **invoice_data(
                    self.contract,
                    gross_value=Decimal("6000.00"),
                    accepted_value=Decimal("6000.00"),
                ),
            )

    def test_contract_position_contains_payment_evidence(self):
        payment = self.create_payment(amount=Decimal("2500.00"))
        position = contract_financial_position(self.contract)
        self.assertEqual(position.paid_value.value, Decimal("2500.00"))
        self.assertEqual(position.paid_value.evidence[0].source_id, str(payment.pk))

    def test_other_fiscal_cannot_see_and_administrator_is_read_only(self):
        payment = self.create_payment(amount=Decimal("2500.00"))
        url = reverse(
            "contracts:payment_detail",
            args=[self.contract.pk, self.order.pk, self.invoice.pk, payment.pk],
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(self.manager.has_perm("contracts.add_payment"))
        self.assertTrue(self.manager.has_perm("contracts.view_payment"))

    def test_canceled_work_order_makes_payment_read_only(self):
        payment = self.create_payment(amount=Decimal("2500.00"))
        type(self.order).objects.filter(pk=self.order.pk).update(
            status=WorkOrderStatus.CANCELED
        )
        with self.assertRaisesMessage(ValidationError, "somente leitura"):
            update_payment(
                payment_id=payment.pk,
                actor=self.owner,
                **payment_data(amount=Decimal("2000.00")),
            )
        create_url = reverse(
            "contracts:payment_create",
            args=[self.contract.pk, self.order.pk, self.invoice.pk],
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(create_url).status_code, 403)

    def test_web_form_localizes_value_and_lists_payment_on_invoice(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse(
                "contracts:payment_create",
                args=[self.contract.pk, self.order.pk, self.invoice.pk],
            ),
            {
                "amount": "2.500,00",
                "payment_date": "2026-09-30",
                "competence": "09/2026",
                "status": "Pago conforme fonte",
                "process_number": "PROCESSO-PAG-WEB",
                "attestation_reference": "Atesto WEB",
                "raer_reference": "RAER WEB",
                "homologation_reference": "Termo WEB",
                "evidence_reference": "Comprovante WEB",
                "notes": "",
            },
        )
        payment = Payment.objects.get(process_number="PROCESSO-PAG-WEB")
        self.assertRedirects(
            response,
            reverse(
                "contracts:payment_detail",
                args=[self.contract.pk, self.order.pk, self.invoice.pk, payment.pk],
            ),
        )
        detail = self.client.get(
            reverse(
                "contracts:invoice_detail",
                args=[self.contract.pk, self.order.pk, self.invoice.pk],
            )
        )
        self.assertContains(detail, "2.500,00")
        self.assertContains(detail, "não representa autorização")

    def test_no_delete_route_and_permissions_are_least_privilege(self):
        self.assertTrue(self.owner.has_perm("contracts.add_payment"))
        self.assertTrue(self.owner.has_perm("contracts.change_payment"))
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("payment_delete", route_names)
