"""Valores em R$ sem quebra de linha entre o símbolo e o número (Sprint 18)."""

import re
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase
from django.urls import reverse

from contracts.test_work_orders import WorkOrderBase
from core.notifications import _money


class ValoresSemQuebraTemplatesTests(SimpleTestCase):
    def test_templates_never_separate_symbol_with_breakable_space(self):
        offenders = []
        for template in Path(settings.BASE_DIR, "templates").rglob("*.html"):
            for number, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"R\$[ \t]+\{\{", line):
                    offenders.append(f"{template.name}:{number}")
        self.assertEqual(offenders, [], "Use R$&nbsp;{{ ... }} para o valor não quebrar.")

    def test_notification_values_use_non_breaking_space(self):
        self.assertEqual(_money(Decimal("4526825466.00"))[:3], "R$ ")

    def test_value_cards_keep_value_on_one_line(self):
        with open(finders.find("core/css/app.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn(".kpi-card, .metric-card, .summary-strip > div { container-type: inline-size; }", css)
        self.assertIn(
            ".kpi-card strong, .metric-card strong, .summary-strip strong { white-space: nowrap;", css
        )


class ValoresSemQuebraTelasTests(WorkOrderBase):
    def test_dashboard_and_report_render_non_breaking_values(self):
        self.client.force_login(self.owner)
        for url in (reverse("home"), reverse("contracts:report", args=[self.contract.pk])):
            with self.subTest(url=url):
                content = self.client.get(url).content.decode()
                self.assertIn("R$&nbsp;", content)
                self.assertNotRegex(content, r"R\$ \d")
