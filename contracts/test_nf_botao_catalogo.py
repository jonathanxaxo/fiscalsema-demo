"""Sprint 43: cadastrar NF em OS com serviços do catálogo fica visível e guiado. Dados fictícios."""

from django.urls import reverse

from .test_nf_dimensionada import NfDimensionadaBase


class NfBotaoCatalogoTests(NfDimensionadaBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.owner)
        self.detail = reverse("contracts:work_order_detail", args=[self.contract.pk, self.wo.pk])
        self.create = reverse("contracts:invoice_create", args=[self.contract.pk, self.wo.pk])

    def test_nf_section_has_button_and_explains_homologation(self):
        page = self.client.get(self.detail)
        self.assertContains(page, 'id="notas-fiscais"')
        self.assertContains(page, f'class="button-link button-link-small" href="{self.create}">Cadastrar Nota Fiscal</a>')
        self.assertContains(page, "só podem ser marcados na NF depois de homologados")

    def test_homologated_line_links_to_invoice_with_service_checked(self):
        self.homologate()
        page = self.client.get(self.detail)
        link = f"{self.create}?servico={self.line.pk}"
        self.assertContains(page, "Pronto para faturar · cadastrar NF")
        self.assertContains(page, link)
        self.assertNotContains(page, "só podem ser marcados na NF depois de homologados")
        form = self.client.get(link)
        self.assertContains(form, f'value="{self.line.pk}"')
        self.assertContains(form, "checked")

    def test_empty_service_list_is_explained_in_form(self):
        form = self.client.get(self.create)
        self.assertEqual(form.status_code, 200)
        self.assertContains(form, "Nenhum serviço homologado e ainda não cobrado nesta OS")

    def test_invalid_or_foreign_service_param_is_ignored(self):
        self.assertEqual(self.client.get(f"{self.create}?servico=abc").status_code, 200)
        page = self.client.get(f"{self.create}?servico=999999")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "checked")
