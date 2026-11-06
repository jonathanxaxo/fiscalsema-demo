from django.contrib.staticfiles import finders
from django.urls import reverse

from contracts.models import WorkOrderStatus
from contracts.test_work_orders import WorkOrderBase


class PadronizacaoTelasTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        self.client.force_login(self.owner)

    def test_operational_lists_follow_contract_list_pattern(self):
        for name, label in [
            ("contracts:item_list", "Cadastrar item"),
            ("contracts:work_order_list", "Cadastrar OS"),
            ("contracts:commitment_list", "Cadastrar empenho"),
        ]:
            with self.subTest(name=name):
                response = self.client.get(reverse(name, args=[self.contract.pk]))
                self.assertContains(response, 'class="page-header"')
                self.assertContains(response, 'class="eyebrow"')
                self.assertContains(response, f'">{label}</a>')
                self.assertContains(response, 'class="button-link"')

    def test_work_order_status_is_a_colored_pill(self):
        response = self.client.get(reverse("contracts:work_order_list", args=[self.contract.pk]))
        self.assertContains(response, 'status-pill status-success">Em execução')

    def test_contract_actions_appear_before_registration_details(self):
        content = self.client.get(reverse("contracts:detail", args=[self.contract.pk])).content.decode()
        self.assertLess(content.index('class="action-groups"'), content.index("<dl>"))

    def test_contract_form_uses_two_column_grid(self):
        response = self.client.get(reverse("contracts:create"))
        self.assertContains(response, "form-card form-grid")
        self.assertContains(response, "form-field form-field-wide")

    def test_ai_drafts_page_uses_system_layout(self):
        response = self.client.get(reverse("assistant_drafts:list"))
        self.assertContains(response, "core/img/logo.svg")
        self.assertContains(response, "Rascunhos preparados pela IA")

    def test_mobile_menu_follows_real_header_height(self):
        with open(finders.find("core/js/app.js"), encoding="utf-8") as script:
            self.assertIn("--menu-top", script.read())
        with open(finders.find("core/css/app.css"), encoding="utf-8") as stylesheet:
            self.assertIn("var(--menu-top, 64px)", stylesheet.read())
