from django.urls import reverse

from contracts.models import WorkOrderStatus
from contracts.test_work_orders import WorkOrderBase


class PainelOrdemTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        self.client.force_login(self.owner)

    def content(self):
        return self.client.get(reverse("home")).content.decode()

    def test_priorities_come_before_financial_and_reference_sections(self):
        content = self.content()
        order = [
            'id="contrato-atual-titulo"',
            'class="dashboard-shortcuts"',
            'id="central-titulo"',
            'id="prazos"',
            'id="notas-divergentes"',
            'id="financeiro-titulo"',
            'id="operacional-titulo"',
            'id="itens-titulo"',
            'id="empenhos-titulo"',
            'id="calendario-financeiro-titulo"',
            'id="modulos-titulo"',
            'id="periodos-anuais-titulo"',
        ]
        positions = [content.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions))

    def test_shortcuts_point_to_existing_sections(self):
        content = self.content()
        for target in ["central-titulo", "financeiro-titulo", "operacional-titulo", "itens-titulo", "empenhos-titulo", "modulos-titulo"]:
            with self.subTest(target=target):
                self.assertIn(f'href="#{target}"', content)
                self.assertIn(f'id="{target}"', content)
