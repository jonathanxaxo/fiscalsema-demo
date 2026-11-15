"""Prazos da OS, prazo da fábrica e horas gastas (Sprint 36; referência: FiscalSema Light)."""

from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from core.notifications import _contract_notifications

from .dashboard import build_contract_dashboard
from .forms import WorkOrderForm
from .models import WorkOrderEvent, WorkOrderStatus
from .test_work_orders import WorkOrderBase, work_order_data
from .work_order_deadlines import countdown, deadline_situation, suggested_deadline


class SugestaoDePrazoTests(WorkOrderBase):
    def test_suggested_deadline_is_opening_plus_six_months(self):
        self.assertEqual(suggested_deadline(date(2026, 1, 15)), date(2026, 7, 15))
        self.assertEqual(suggested_deadline(date(2026, 8, 31)), date(2027, 2, 28))
        self.assertEqual(suggested_deadline(date(2027, 8, 31)), date(2028, 2, 29))

    def form_data(self, **overrides):
        data = work_order_data(self.item, **overrides)
        data["item"] = self.item.pk
        data = {key: ("" if value is None else value) for key, value in data.items()}
        for key in ("opening_date", "deadline", "factory_deadline"):
            if hasattr(data.get(key), "isoformat"):
                data[key] = data[key].isoformat()
        data["hours"] = "40"
        return data

    def test_form_fills_deadline_on_create_and_has_browser_hint(self):
        form = WorkOrderForm(data=self.form_data(deadline=None), contract=self.contract)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["deadline"], date(2027, 3, 28))
        html = str(form["deadline"])
        self.assertIn('data-suggest-from="opening_date"', html)
        self.assertIn('data-suggest-months="6"', html)
        self.assertEqual(form.fields["deadline"].label, "Prazo contratual (abertura + 6 meses)")

    def test_typed_deadline_is_kept(self):
        form = WorkOrderForm(data=self.form_data(deadline=date(2026, 12, 1)), contract=self.contract)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["deadline"], date(2026, 12, 1))


class CamposNovosTests(WorkOrderBase):
    def test_factory_deadline_and_spent_hours_rules(self):
        with self.assertRaises(ValidationError) as error:
            self.create_work_order(factory_deadline=date(2026, 9, 1))
        self.assertIn("factory_deadline", error.exception.message_dict)
        with self.assertRaises(ValidationError) as error:
            self.create_work_order(spent_hours=Decimal("-1"))
        self.assertIn("spent_hours", error.exception.message_dict)

    def test_spent_hours_are_informative_and_audited(self):
        work_order = self.create_work_order(
            factory_deadline=date(2026, 10, 20), spent_hours=Decimal("35"),
        )
        self.assertEqual(work_order.spent_hours_difference, Decimal("5"))
        self.assertEqual(work_order.total_value, Decimal("40") * Decimal("250.00"))
        event = WorkOrderEvent.objects.filter(work_order=work_order).first()
        self.assertEqual(event.details["atual"]["prazo_fabrica"], "2026-10-20")
        self.assertEqual(Decimal(event.details["atual"]["horas_gastas_informadas"]), Decimal("35"))


class SituacaoTests(WorkOrderBase):
    def test_countdown_texts_and_colors(self):
        self.assertEqual((countdown(10).text, countdown(10).tone), ("faltam 10 dias", "success"))
        self.assertEqual((countdown(7).text, countdown(7).tone), ("faltam 7 dias", "warning"))
        self.assertEqual(countdown(1).text, "falta 1 dia")
        self.assertEqual((countdown(0).text, countdown(0).tone), ("vence hoje", "warning"))
        self.assertEqual((countdown(-3).text, countdown(-3).tone), ("vencido há 3 dias", "danger"))
        self.assertEqual(countdown(None).text, "não informado")

    def test_situations(self):
        today = date(2026, 10, 10)
        wo = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS, deadline=date(2026, 10, 31),
                                    factory_deadline=date(2026, 10, 15))
        situation = deadline_situation(wo, today)
        self.assertEqual(situation.code, "factory_due")
        self.assertEqual(situation.label, "Cobrar a fábrica: entrega em 5 dias")
        self.assertEqual(deadline_situation(wo, date(2026, 10, 16)).code, "factory_overdue")
        late = deadline_situation(wo, date(2026, 11, 2))
        self.assertEqual((late.code, late.label), ("late", "Em atraso há 2 dias (prazo contratual)"))
        self.assertEqual(deadline_situation(wo, date(2026, 10, 1)).code, "on_time")
        wo.status, wo.completion_date = WorkOrderStatus.COMPLETED, date(2026, 11, 5)
        done = deadline_situation(wo, today)
        self.assertEqual((done.label, done.contract_countdown), ("Entregue com atraso", None))


class AvisosETelasTests(WorkOrderBase):
    def test_factory_alert_in_dashboard_bell_and_screens(self):
        today = timezone.localdate()
        wo = self.create_work_order(
            status=WorkOrderStatus.IN_PROGRESS, opening_date=today - timedelta(days=10),
            deadline=today + timedelta(days=60), factory_deadline=today + timedelta(days=3),
            spent_hours=Decimal("12"),
        )
        dashboard = build_contract_dashboard(self.contract)
        self.assertEqual([a.work_order for a in dashboard.factory_deadline_alerts], [wo])
        titles = [note["title"] for note in _contract_notifications(self.contract, dashboard, can_fix=True)]
        self.assertTrue(any("Cobrar a fábrica" in title and "em 3 dias" in title for title in titles), titles)
        self.client.force_login(self.owner)
        detail = self.client.get(reverse("contracts:work_order_detail", args=[self.contract.pk, wo.pk]))
        self.assertContains(detail, "Cobrar a fábrica: entrega em 3 dias")
        self.assertContains(detail, "faltam 3 dias")
        self.assertContains(detail, "faltam 60 dias")
        self.assertContains(detail, "Horas gastas informadas pela fábrica")
        listing = self.client.get(reverse("contracts:work_order_list", args=[self.contract.pk]))
        self.assertContains(listing, "Situação do prazo")
        home = self.client.get(reverse("home"), {"contract": self.contract.pk})
        self.assertContains(home, "Cobrar a fábrica:")
        report = self.client.get(reverse("contracts:report", args=[self.contract.pk]))
        self.assertContains(report, "Prazos e horas informados nas OS")
