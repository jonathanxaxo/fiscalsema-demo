from decimal import Decimal

from django.urls import reverse

from contracts.models import WorkOrderStatus
from contracts.services import create_invoice
from contracts.test_invoices import invoice_data
from contracts.test_work_orders import WorkOrderBase


class PainelOrdemTests(WorkOrderBase):
    """Layout aprovado na Sprint 13 (substitui a ordem da Sprint 08)."""

    def setUp(self):
        super().setUp()
        self.overdue = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        create_invoice(
            work_order_id=self.overdue.pk,
            actor=self.owner,
            **invoice_data(self.contract, gross_value=Decimal("1000.00"), accepted_value=Decimal("1000.00")),
        )
        self.client.force_login(self.owner)

    def content(self):
        return self.client.get(reverse("home")).content.decode()

    def test_sections_follow_approved_layout(self):
        content = self.content()
        order = [
            'id="contrato-atual-titulo"',
            'id="modulos-titulo"',
            'id="financeiro-titulo"',
            'id="central-titulo"',
            'id="operacional-titulo"',
            'id="ciclo-titulo"',
            'id="itens-titulo"',
            'id="empenhos-titulo"',
            'class="surface more-details"',
            'id="calendario-financeiro-titulo"',
            'id="periodos-anuais-titulo"',
        ]
        positions = [content.index(marker) for marker in order]
        self.assertEqual(positions, sorted(positions))

    def test_attention_list_groups_pending_items_with_readable_labels(self):
        content = self.content()
        self.assertIn('class="attention-list"', content)
        self.assertIn(f"<strong>OS {self.overdue.number}</strong> venceu em", content)
        self.assertIn('class="count-badge"', content)
        self.assertNotIn("COM_PENDENCIA", content)

    def test_main_indicators_have_progress_bars(self):
        content = self.content()
        for label in ("Contratado", "Empenhado ativo", "Executado", "Pago", "Saldo contratual"):
            with self.subTest(label=label):
                self.assertIn(f"<small>{label}</small>", content)
        self.assertIn('class="progress"', content)
