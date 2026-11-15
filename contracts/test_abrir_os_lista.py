"""Sprint 47: na lista de OS, clicar na OS abre a OS; na OS, NF e edição ficam no topo. Dados fictícios."""

from django.urls import reverse

from .test_nf_dimensionada import NfDimensionadaBase


class AbrirOsListaTests(NfDimensionadaBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.detail = reverse("contracts:work_order_detail", args=[self.contract.pk, self.wo.pk])

    def test_list_number_and_row_open_the_work_order(self):
        page = self.client.get(reverse("contracts:work_order_list", args=[self.contract.pk]))
        self.assertContains(page, f'data-row-link="{self.detail}"')
        self.assertContains(page, f'<a class="row-link-main" href="{self.detail}">{self.wo.number}</a>')
        self.assertContains(page, ">Abrir</a>")  # o botão antigo continua

    def test_detail_has_invoice_and_edit_at_the_top_and_keeps_bottom_links(self):
        html = self.client.get(self.detail).content.decode()
        top = html[html.index("<h1>"):html.index("<dl>")]
        self.assertIn(reverse("contracts:invoice_create", args=[self.contract.pk, self.wo.pk]), top)
        self.assertIn(reverse("contracts:work_order_update", args=[self.contract.pk, self.wo.pk]), top)
        self.assertEqual(html.count(">Cadastrar Nota Fiscal</a>"), 3)  # topo, seção de NF e rodapé
        self.assertIn(">Editar OS</a>", html[html.index('id="notas-fiscais"'):])

    def test_table_mode_number_links_to_work_order(self):
        page = self.client.get(reverse("contracts:table_mode", args=[self.contract.pk]) + "?tipo=work_orders")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, f'<a href="{self.detail}">{self.wo.number}</a>')
