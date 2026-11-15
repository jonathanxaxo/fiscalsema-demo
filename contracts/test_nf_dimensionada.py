"""NF ligada aos serviços homologados, valor dimensionado e devolução (Sprint 39).

Referência: FiscalSema Light (somente lido). Dados fictícios.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse

from core.notifications import _contract_notifications

from .dashboard import build_contract_dashboard
from .models import InvoiceEvent
from .service_catalog import (
    accept_service_line, homologate_service_line, register_service_line_delivery,
)
from .services import (
    contract_financial_position, create_invoice, create_payment, return_invoice, update_invoice,
)
from .test_catalogo_servicos import CatalogoBase
from .test_invoices import invoice_data
from .test_payments import payment_data


class NfDimensionadaBase(CatalogoBase):
    def setUp(self):
        super().setUp()
        self.line = self.add(quantity=Decimal("10"))  # 10 × 3,5 = 35 UST × R$ 10,00 = R$ 350,00
        self.add(quantity=Decimal("20"))  # outro serviço da OS (OS total: 105 UST = R$ 1.050,00)

    def homologate(self, line=None):
        line = line or self.line
        register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=self.today)
        accept_service_line(line_id=line.pk, actor=self.owner, accepted_at=self.today)
        homologate_service_line(line_id=line.pk, actor=self.owner, homologated_at=self.today,
                                reference="Termo fictício 7/2026")
        line.refresh_from_db()
        return line

    def invoice(self, value, **extra):
        data = invoice_data(self.contract, issue_date=self.today, competence=self.today.strftime("%m/%Y"),
                            gross_value=Decimal(value), accepted_value=Decimal(value), **extra)
        return create_invoice(work_order_id=self.wo.pk, actor=self.owner, **data)


class VinculoTests(NfDimensionadaBase):
    def test_only_homologated_lines_can_be_billed(self):
        with self.assertRaises(ValidationError) as error:
            self.invoice("350.00", service_lines=[self.line])
        self.assertIn("ainda não foi homologado", str(error.exception))

    def test_dimensioned_value_and_difference(self):
        self.homologate()
        exact = self.invoice("350.00", service_lines=[self.line])
        self.assertEqual(exact.dimensioned_value, Decimal("350.00"))
        self.assertFalse(exact.dimensioned_difference)
        self.assertEqual(self.line.billing_label, f"NF {exact.number}/{exact.series} · Faturada")
        with self.assertRaises(ValidationError) as error:  # mesmo serviço em duas NF ativas
            self.invoice("350.00", number="NF-002", service_lines=[self.line])
        self.assertIn("já está na NF", str(error.exception))

    def test_divergent_invoice_alerts(self):
        self.homologate()
        divergent = self.invoice("400.00", service_lines=[self.line])
        self.assertEqual(divergent.dimensioned_difference, Decimal("50.00"))
        dashboard = build_contract_dashboard(self.contract)
        self.assertEqual(dashboard.dimensioned_divergences, (divergent,))
        titles = [n["title"] for n in _contract_notifications(self.contract, dashboard, can_fix=True)]
        self.assertTrue(any("diferente do dimensionado" in t for t in titles), titles)


class DevolucaoTests(NfDimensionadaBase):
    def test_return_removes_invoice_from_calculations_and_allows_replacement(self):
        self.homologate()
        wrong = self.invoice("400.00", service_lines=[self.line])
        self.assertEqual(contract_financial_position(self.contract).invoiced_gross_value.value, Decimal("400.00"))
        return_invoice(invoice_id=wrong.pk, actor=self.owner, returned_at=self.today,
                       reason="Valor diferente do dimensionado")
        wrong.refresh_from_db()
        self.assertTrue(wrong.is_returned)
        self.assertEqual(contract_financial_position(self.contract).invoiced_gross_value.value, Decimal("0.00"))
        self.assertTrue(InvoiceEvent.objects.filter(invoice=wrong, event_type="NF_DEVOLVIDA").exists())
        dashboard = build_contract_dashboard(self.contract)
        self.assertEqual(dashboard.returned_awaiting_correction, (wrong,))
        # NF devolvida: somente leitura e sem pagamento
        with self.assertRaises(ValidationError):
            update_invoice(invoice_id=wrong.pk, actor=self.owner, **invoice_data(self.contract, gross_value=Decimal("350.00")))
        with self.assertRaises(ValidationError):
            create_payment(invoice_id=wrong.pk, actor=self.owner, **payment_data(amount=Decimal("1.00")))
        # NF corrigida cobra o mesmo serviço e substitui a devolvida
        fixed = self.invoice("350.00", number="NF-002", service_lines=[self.line], replaces=wrong)
        self.assertEqual(fixed.replaces, wrong)
        self.assertEqual(build_contract_dashboard(self.contract).returned_awaiting_correction, ())
        with self.assertRaises(ValidationError):  # só uma substituição
            self.invoice("1.00", number="NF-003", replaces=wrong)

    def test_return_rules(self):
        self.homologate()
        nf = self.invoice("350.00", service_lines=[self.line])
        with self.assertRaises(ValidationError):
            return_invoice(invoice_id=nf.pk, actor=self.owner, returned_at=self.today, reason="  ")
        with self.assertRaises(ValidationError):
            return_invoice(invoice_id=nf.pk, actor=self.owner, returned_at=self.today + timedelta(days=1), reason="x")
        create_payment(invoice_id=nf.pk, actor=self.owner,
                       **payment_data(amount=Decimal("350.00"), payment_date=self.today,
                                      competence=self.today.strftime("%m/%Y")))
        with self.assertRaises(ValidationError):
            return_invoice(invoice_id=nf.pk, actor=self.owner, returned_at=self.today, reason="Pago não volta")


class TelaTests(NfDimensionadaBase):
    def test_invoice_screen_and_return_flow(self):
        self.homologate()
        nf = self.invoice("400.00", service_lines=[self.line])
        self.client.force_login(self.owner)
        detail_url = reverse("contracts:invoice_detail", args=[self.contract.pk, self.wo.pk, nf.pk])
        detail = self.client.get(detail_url)
        self.assertContains(detail, "Valor da NF × valor dimensionado")
        self.assertContains(detail, "Devolver para correção")
        response = self.client.post(reverse("contracts:invoice_return", args=[self.contract.pk, self.wo.pk, nf.pk]),
                                    {"returned_at": self.today.isoformat(), "reason": "Valor diferente"})
        self.assertRedirects(response, detail_url, fetch_redirect_response=False)
        after = self.client.get(detail_url)
        self.assertContains(after, "NF devolvida para correção")
        self.assertNotContains(after, "Registrar pagamento")
        form = self.client.get(reverse("contracts:invoice_create", args=[self.contract.pk, self.wo.pk]))
        self.assertContains(form, "Substitui a NF devolvida")
        self.assertContains(form, "Serviços cobrados nesta NF")
