"""Padrão único de botões e textos legíveis de conferência (Sprint 16)."""

import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.urls import reverse

from contracts.services import create_invoice
from contracts.test_invoices import invoice_data
from contracts.test_work_orders import WorkOrderBase
from contracts.models import WorkOrderStatus


class PadraoBotoesTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        order = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        create_invoice(
            work_order_id=order.pk,
            actor=self.owner,
            **invoice_data(self.contract, gross_value=Decimal("1000.00"), accepted_value=Decimal("1000.00")),
        )
        self.client.force_login(self.owner)

    def test_report_uses_system_layout_and_standard_buttons(self):
        response = self.client.get(reverse("contracts:report", args=[self.contract.pk]))
        self.assertTemplateUsed(response, "accounts/base.html")
        content = response.content.decode()
        self.assertIn("core/img/logo.svg", content)
        self.assertNotIn('class="button"', content)
        self.assertIn('class="button-link button-link-secondary"', content)
        self.assertIn("Limpar filtros", content)

    def test_check_codes_are_shown_as_readable_labels(self):
        for name in ("contracts:report", "contracts:accountability"):
            with self.subTest(name=name):
                content = self.client.get(reverse(name, args=[self.contract.pk])).content.decode()
                self.assertNotIn(">COM_PENDENCIA<", content)
                self.assertNotIn(">CONFERIDA<", content)
                self.assertIn('class="status-pill', content)

    def test_action_rows_have_no_dot_separators(self):
        templates = Path(settings.BASE_DIR) / "templates"
        offenders = []
        for path in templates.rglob("*.html"):
            for row in re.findall(r'<p class="(?:actions|toolbar)[^"]*">.*?</p>', path.read_text(encoding="utf-8"), re.S):
                if re.search(r"(</a>|%\})\s*·", row):
                    offenders.append(str(path.relative_to(templates)))
        self.assertEqual(offenders, [])

    def test_two_standard_button_sizes(self):
        with open(finders.find("core/css/app.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn("button, .button-link { min-height: 40px;", css)
        self.assertIn(".button-link-small { min-height: 34px;", css)
        self.assertIn(".inline-form button { min-height: 34px;", css)
        self.assertIn(".app-page .actions > a:not(.button-link), .app-page .toolbar > a:not(.button-link) { min-height: 40px;", css)
