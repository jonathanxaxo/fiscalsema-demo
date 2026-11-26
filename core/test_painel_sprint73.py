"""Sprint 73: indicadores explicados, urgência visível na Central de trabalho e atalhos."""

from decimal import Decimal

from django.urls import reverse

from contracts.models import WorkOrderStatus
from contracts.services import contracts_with_access_management_visible_to, create_invoice
from contracts.test_invoices import invoice_data
from contracts.test_work_orders import WorkOrderBase


class PainelSprint73Tests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.overdue = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        create_invoice(
            work_order_id=self.overdue.pk,
            actor=self.owner,
            **invoice_data(self.contract, gross_value=Decimal("1000.00"), accepted_value=Decimal("1000.00")),
        )
        self.client.force_login(self.owner)

    def get(self):
        return self.client.get(reverse("home"), {"contract": self.contract.pk})

    def test_each_indicator_has_short_explanation(self):
        content = self.get().content.decode()
        for texto in (
            "Valor atual, com as alterações vigentes",
            "Soma dos empenhos ativos",
            "Execuções registradas nas OS",
            "Pagamentos registrados nas NF",
            "Contratado menos o comprometido em OS",
            "(OS assinadas, em execução ou concluídas)",
            "(valor bruto das NF ativas)",
        ):
            with self.subTest(texto=texto):
                self.assertIn(texto, content)

    def test_definitions_block_matches_financial_engine(self):
        content = self.get().content.decode()
        self.assertIn("O que significa cada valor?", content)
        self.assertIn("Nenhuma fórmula é alterada aqui.", content)
        # Mesmo critério de calculate_contract_financial_position: saldo = valor atual - comprometido.
        self.assertIn("Contratado menos o comprometido em OS. É o quanto ainda pode virar nova OS.", content)
        self.assertIn("OS em rascunho, abertas, suspensas ou canceladas não entram.", content)

    def test_financial_values_are_unchanged(self):
        response = self.get()
        position = response.context["dashboard"].financial_position
        self.assertEqual(
            position.contract_balance.value,
            self.contract.current_value - position.committed_value.value,
        )

    def test_work_center_shows_urgency_with_existing_criteria(self):
        response = self.get()
        dashboard = response.context["dashboard"]
        self.assertGreaterEqual(dashboard.urgent_count, 1)  # a OS vencida
        self.assertEqual(dashboard.warning_count, dashboard.attention_count - dashboard.urgent_count)
        content = response.content.decode()
        self.assertIn(f"{dashboard.urgent_count} urgente", content)
        self.assertIn(f"{dashboard.warning_count} de atenção", content)
        urgente = content.index('<b class="urgency urgency-high">Urgente</b><span><strong>OS')
        self.assertLess(urgente, content.index(f"<strong>OS {self.overdue.number}</strong> venceu em"))
        if dashboard.warning_count:
            self.assertLess(urgente, content.index('<b class="urgency">Atenção</b>'))

    def test_shortcuts_point_to_existing_features(self):
        response = self.get()
        content = response.content.decode()
        self.assertIn('href="#notas-pendentes">Notas e pagamentos</a>', content)
        self.assertIn('id="notas-pendentes"', content)
        if response.context.get("assistant_enabled"):
            self.assertIn(f'{reverse("assistant:chat")}?contract={self.contract.pk}">Perguntar ao Arise</a>', content)
        pode_auditar = contracts_with_access_management_visible_to(self.owner).filter(pk=self.contract.pk).exists()
        self.assertEqual(response.context["can_view_contract_audit"], pode_auditar)
        link = f'href="{reverse("audit:contract", args=[self.contract.pk])}">Auditoria</a>'
        self.assertEqual(link in content, pode_auditar)

    def test_individual_dashboard_uses_same_audit_rule(self):
        response = self.client.get(reverse("contracts:dashboard", args=[self.contract.pk]))
        self.assertEqual(response.status_code, 200)
        pode_auditar = contracts_with_access_management_visible_to(self.owner).filter(pk=self.contract.pk).exists()
        self.assertEqual(response.context["can_view_contract_audit"], pode_auditar)
        self.assertIn("O que significa cada valor?", response.content.decode())
