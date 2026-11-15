"""Sprint 48: clicar na linha abre o registro no sistema inteiro, sem tirar nenhum botão. Dados fictícios."""

from django.contrib.staticfiles import finders
from django.urls import reverse

from .test_nf_dimensionada import NfDimensionadaBase


class LinhasClicaveisTests(NfDimensionadaBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.c = self.contract.pk

    def test_lists_with_action_column_have_row_link_and_keep_buttons(self):
        casos = (
            (reverse("contracts:list"), reverse("contracts:detail", args=[self.c]), "Abrir cadastro"),
            (reverse("contracts:item_list", args=[self.c]), reverse("contracts:item_detail", args=[self.c, self.ust_item.pk]), ">Abrir<"),
        )
        for lista, destino, botao in casos:
            page = self.client.get(lista)
            self.assertContains(page, f'data-row-link="{destino}"')
            self.assertContains(page, botao)

    def test_invoice_rows_inside_work_order_open_the_invoice(self):
        self.homologate()
        invoice = self.invoice("350.00", service_lines=[self.line])
        page = self.client.get(reverse("contracts:work_order_detail", args=[self.c, self.wo.pk]))
        self.assertContains(page, f'data-row-link="{reverse("contracts:invoice_detail", args=[self.c, self.wo.pk, invoice.pk])}"')

    def test_table_mode_rows_open_detail_pages(self):
        page = self.client.get(reverse("contracts:table_mode", args=[self.c]) + "?tipo=items")
        self.assertContains(page, f'data-row-link="{reverse("contracts:item_detail", args=[self.c, self.ust_item.pk])}"')

    def test_generic_rule_uses_first_cell_link_and_skips_chat(self):
        script = open(finders.find("core/js/app.js"), encoding="utf-8").read()
        self.assertIn("row.cells[0].querySelector('a[href]", script)
        self.assertIn("[data-no-row-link], .assistant-messages, .arise-panel", script)
        self.assertIn("event.target.closest('a, button, input, select, textarea, label, form, summary')", script)
