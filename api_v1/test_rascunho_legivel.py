"""Sprint 61: o rascunho da IA aparece escrito em português, sem exigir leitura de código."""
from django.test import SimpleTestCase

from contracts.forms import ContractForm

from .leitura import reais, valor_legivel
from .models import AssistantDraft
from .tests import ControlledAssistantDraftTests


class ValorLegivelTests(SimpleTestCase):
    def test_reais_no_formato_brasileiro(self):
        self.assertEqual(reais("4000.00"), "R$ 4.000,00")
        self.assertEqual(reais("1234567.5"), "R$ 1.234.567,50")

    def test_datas_numeros_e_vazios(self):
        self.assertEqual(valor_legivel("execution_date", "2026-11-18"), "18/11/2026")
        self.assertEqual(valor_legivel("executed_value", "4000.00"), "R$ 4.000,00")
        self.assertEqual(valor_legivel("executed_quantity", "20"), "20")
        self.assertEqual(valor_legivel("notes", None), "—")
        self.assertEqual(valor_legivel("notes", ""), "—")
        self.assertEqual(valor_legivel("is_active", True), "Sim")


class RascunhoLegivelTests(ControlledAssistantDraftTests):
    def _rascunho(self):
        response = self.create_draft()
        self.assertEqual(response.status_code, 201, response.content)
        return AssistantDraft.objects.get(pk=response.json()["data"]["id"])

    def test_proposta_aparece_escrita_para_o_fiscal(self):
        draft = self._rascunho()
        self.client.force_login(self.owner)
        html = self.client.get(f"/rascunhos-ia/{draft.pk}/").content.decode()

        self.assertIn("O que a IA está propondo", html)
        self.assertIn(str(ContractForm.base_fields["number"].label), html)
        self.assertIn("01/02/2026", html)
        self.assertIn("Novo", html)
        self.assertIn("De onde veio a informação", html)
        self.assertIn("Documento informado pelo Fiscal", html)
        self.assertIn("referência: REF-001", html)
        # Ainda é só uma proposta, com a decisão humana em destaque.
        self.assertIn("NÃO EXECUTADO", html)
        self.assertIn("Aprovar e executar", html)

    def test_codigo_fica_guardado_para_auditoria(self):
        draft = self._rascunho()
        self.client.force_login(self.owner)
        html = self.client.get(f"/rascunhos-ia/{draft.pk}/").content.decode()
        tecnico = html.index('<details class="draft-technical">')
        # O JSON continua disponível, mas só dentro da área técnica recolhida.
        self.assertGreater(html.index("&quot;classification&quot;"), tecnico)
        self.assertLess(html.index("O que a IA está propondo"), tecnico)

    def test_resultado_da_conferencia_aparece_escrito(self):
        draft = self._rascunho()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(f"/rascunhos-ia/{draft.pk}/confirmar/").status_code, 302)
        html = self.client.get(f"/rascunhos-ia/{draft.pk}/").content.decode()
        self.assertIn("Conferência feita pelo sistema", html)
        self.assertIn("O sistema conferiu o registro", html)
        self.assertIn("Registro gravado no sistema:", html)
        self.assertNotIn("contracts.contract #", html)
        self.assertIn("Saldo do contrato", html)
        self.assertIn("R$", html)
