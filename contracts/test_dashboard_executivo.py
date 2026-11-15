"""Dashboard executivo do contrato (Sprint 37; referência: FiscalSema Light). Dados fictícios."""

from datetime import date, timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile

from .executive_dashboard import build_monthly_evolution, build_validity_progress
from .models import WorkOrderStatus
from .test_work_orders import WorkOrderBase


class VigenciaEEvolucaoTests(WorkOrderBase):
    def test_validity_progress(self):
        self.contract.validity_start, self.contract.validity_end = date(2026, 1, 1), date(2026, 12, 31)
        middle = build_validity_progress(self.contract, today=date(2026, 7, 1))
        self.assertEqual((middle.elapsed_days, middle.total_days), (182, 365))
        self.assertEqual(middle.percentage, Decimal("49.86"))
        before = build_validity_progress(self.contract, today=date(2025, 12, 1))
        self.assertEqual((before.elapsed_days, before.has_started), (0, False))
        after = build_validity_progress(self.contract, today=date(2027, 2, 1))
        self.assertEqual((after.percentage, after.has_ended), (Decimal("100.00"), True))

    def test_monthly_evolution_window_and_zero_months(self):
        evolution = build_monthly_evolution(self.contract, today=date(2026, 3, 15))
        self.assertEqual([e.label for e in evolution.entries], ["01/2026", "02/2026", "03/2026"])
        self.assertTrue(all(e.executed == 0 and e.invoiced == 0 and e.paid == 0 for e in evolution.entries))
        long = build_monthly_evolution(self.contract, today=date(2027, 6, 1))
        self.assertEqual(len(long.entries), 12)
        self.assertEqual(long.entries[-1].label, "01/2027")
        empty = build_monthly_evolution(self.contract, today=date(2025, 1, 1))
        self.assertEqual(empty.entries, ())


class TelaTests(WorkOrderBase):
    def test_page_shows_sections_and_only_visible_contracts(self):
        today = timezone.localdate()
        self.create_work_order(status=WorkOrderStatus.IN_PROGRESS, opening_date=today - timedelta(days=5),
                               deadline=today + timedelta(days=20), factory_deadline=today + timedelta(days=2))
        self.client.force_login(self.owner)
        page = self.client.get(reverse("contracts:executive_dashboard"))
        self.assertEqual(page.status_code, 200)
        for text in ("Dashboard do contrato", "Tempo decorrido x execução", "Situação das OS",
                     "OS abertas e prazos", "Consumo e saldo por item", "Executado, faturado e pago por mês",
                     "Cobrar a fábrica: entrega em 2 dias", "Horas informadas nas OS"):
            self.assertContains(page, text)
        self.assertContains(page, 'aria-current="page"', html=False)
        self.assertContains(page, "Valor do contrato: <strong>R$&nbsp;100.000,00</strong>", html=False)
        self.assertNotContains(page, "(R$&nbsp;)", html=False)
        # outra pessoa sem acesso não vê o contrato
        self.client.force_login(self.other)
        self.assertContains(self.client.get(reverse("contracts:executive_dashboard")), "Nenhum contrato disponível")
        self.assertEqual(self.client.get(reverse("contracts:executive_dashboard"),
                                         {"contract": self.contract.pk}).status_code, 404)
        self.assertEqual(self.client.get(reverse("contracts:executive_dashboard"),
                                         {"contract": "abc"}).status_code, 404)

    def test_administrator_is_refused_and_menu_link(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("contracts:executive_dashboard")).status_code, 403)
        self.client.force_login(self.owner)
        home = self.client.get(reverse("home"))
        self.assertContains(home, reverse("contracts:executive_dashboard"))
