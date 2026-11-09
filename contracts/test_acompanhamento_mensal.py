"""Acompanhamento mensal de OS (Sprint 19, adaptado do sistema principal)."""

from datetime import date
from decimal import Decimal

from django.urls import reverse

from contracts.dashboard import build_contract_dashboard
from contracts.forms import WorkOrderForm
from contracts.models import ContractItemUnit, WorkOrderEvent, WorkOrderStatus
from contracts.services import (
    create_contract_item,
    create_invoice,
    create_payment,
    create_work_order,
    create_work_order_execution,
    update_work_order,
)
from contracts.test_executions import execution_data
from contracts.test_invoices import invoice_data
from contracts.test_items import item_data
from contracts.test_payments import payment_data
from contracts.test_work_orders import WorkOrderBase, work_order_data
from core.notifications import build_notifications

SEPTEMBER = date(2026, 9, 30)


class AcompanhamentoMensalTests(WorkOrderBase):
    def monthly_order(self, **overrides):
        data = {"status": WorkOrderStatus.IN_PROGRESS, "monthly_follow_up": True}
        data.update(overrides)
        return self.create_work_order(**data)

    def attentions(self, today=SEPTEMBER):
        return build_contract_dashboard(self.contract, today=today).monthly_work_order_attentions

    def test_field_defaults_to_false_and_unmarked_orders_are_ignored(self):
        order = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        self.assertFalse(order.monthly_follow_up)
        self.assertEqual(self.attentions(), ())

    def test_marked_order_without_records_is_pending_in_red(self):
        order = self.monthly_order()
        (entry,) = self.attentions()
        self.assertEqual(entry.work_order, order)
        self.assertEqual(entry.competence, "09/2026")
        self.assertEqual(entry.state, "Atualização da competência pendente")
        self.assertEqual(entry.tone, "danger")
        self.assertEqual(entry.source, "marcação explícita da OS")

    def test_execution_invoice_and_payment_of_the_month_change_the_state(self):
        order = self.monthly_order()
        create_work_order_execution(work_order_id=order.pk, actor=self.owner, **execution_data())
        self.assertEqual(
            self.attentions()[0].state,
            "Execução atualizada; aguardando NF e conferência documental",
        )
        invoice = create_invoice(
            work_order_id=order.pk,
            actor=self.owner,
            **invoice_data(self.contract, gross_value=Decimal("2500.00"), accepted_value=Decimal("2500.00")),
        )
        self.assertEqual(
            self.attentions()[0].state,
            "NF cadastrada; conferir Atesto, RAER, homologação e pagamento",
        )
        create_payment(invoice_id=invoice.pk, actor=self.owner, **payment_data(amount=Decimal("2500.00")))
        entry = self.attentions()[0]
        self.assertEqual(entry.state, "Pagamento registrado para a competência")
        self.assertEqual(entry.tone, "success")

    def test_records_of_another_month_do_not_count(self):
        order = self.monthly_order()
        create_work_order_execution(work_order_id=order.pk, actor=self.owner, **execution_data())
        self.assertEqual(self.attentions(today=date(2026, 10, 15))[0].tone, "danger")

    def test_item_with_month_unit_enters_automatically(self):
        month_item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(
                number="2",
                unit=ContractItemUnit.MONTH,
                contracted_quantity=Decimal("12.0000"),
                unit_value=Decimal("1000.00"),
            ),
        )
        order = create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(
                month_item, hours=None, quantity=Decimal("1.0000"), status=WorkOrderStatus.IN_PROGRESS
            ),
        )
        (entry,) = self.attentions()
        self.assertEqual(entry.work_order, order)
        self.assertEqual(entry.source, "unidade contratual Mês")

    def test_suspended_is_warning_and_closed_orders_leave_the_list(self):
        self.monthly_order(status=WorkOrderStatus.SUSPENDED)
        self.monthly_order(number="OS-002/2026", status=WorkOrderStatus.COMPLETED, completion_date=SEPTEMBER)
        (entry,) = self.attentions()
        self.assertEqual(entry.tone, "warning")
        self.assertEqual(entry.state, "OS suspensa; conferir providência e vigência")

    def test_marking_is_audited(self):
        order = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        data = work_order_data(self.item, status=WorkOrderStatus.IN_PROGRESS, monthly_follow_up=True)
        update_work_order(work_order_id=order.pk, actor=self.owner, **data)
        event = WorkOrderEvent.objects.filter(work_order=order).latest("pk")
        self.assertFalse(event.details["anterior"]["acompanhamento_mensal"])
        self.assertTrue(event.details["atual"]["acompanhamento_mensal"])

    def test_form_offers_the_checkbox(self):
        form = WorkOrderForm(contract=self.contract)
        self.assertIn("monthly_follow_up", form.fields)
        self.assertIn("faturamento mensal", form.fields["monthly_follow_up"].help_text)

    def test_screens_show_the_follow_up(self):
        order = self.monthly_order()
        self.client.force_login(self.owner)
        home = self.client.get(reverse("home"))
        self.assertContains(home, "Acompanhamento mensal de OS")
        self.assertContains(home, "Atualização da competência pendente")
        self.assertContains(home, "não autoriza pagamento")
        listing = self.client.get(reverse("contracts:work_order_list", args=[self.contract.pk]))
        self.assertContains(listing, '<span class="status-pill status-warning">Mensal</span>', html=True)
        detail = self.client.get(reverse("contracts:work_order_detail", args=[self.contract.pk, order.pk]))
        self.assertContains(detail, "Sim — acompanhar a competência no painel")

    def test_bell_notifies_pending_but_not_paid(self):
        order = self.monthly_order()
        notes = build_notifications(self.owner)["items"]
        monthly = [n for n in notes if "(mensal)" in n["title"]]
        self.assertEqual(len(monthly), 1)
        self.assertEqual(monthly[0]["level"], "danger")
        self.assertEqual(
            monthly[0]["url"], reverse("contracts:work_order_detail", args=[self.contract.pk, order.pk])
        )
        self.assertEqual(monthly[0]["hint"], "Abrir OS para atualizar o mês")
