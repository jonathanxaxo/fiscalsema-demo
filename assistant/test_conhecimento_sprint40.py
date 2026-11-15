"""Base de conhecimento do Arise cobre as funções das Sprints 35 a 39 (Sprint 40)."""

from django.test import SimpleTestCase

from assistant.conhecimento import help_text, select_sections


class ConhecimentoFuncoesNovasTests(SimpleTestCase):
    CASES = {
        "Como cadastro um serviço no catálogo com UST?": "14-catalogo-servicos",
        "Como homologar um serviço aceito com o termo?": "14-catalogo-servicos",
        "Como devolvo uma NF com valor diferente do dimensionado?": "15-nf-dimensionada",
        "O que é o prazo da fábrica e como cobrar?": "13-prazos-os",
        "Onde fica o dashboard executivo com gráfico de evolução mensal?": "12-dashboard-executivo",
        "Posso digitar o CNPJ com pontos?": "02-contratos",
    }

    def test_each_new_feature_finds_its_help_section(self):
        for question, section in self.CASES.items():
            names = [item.name for item in select_sections(question, profile="FISCAL")]
            self.assertIn(section, names[:3], question)

    def test_help_text_explains_paths_and_limits(self):
        text = help_text("Como devolver NF e cadastrar a NF corrigida?", profile="FISCAL")
        self.assertIn("Devolver para correção", text)
        self.assertIn("Substitui a NF devolvida", text)
        text = help_text("Como homologar serviço do catálogo?", profile="FISCAL")
        self.assertIn("a IA nunca homologa", text)
        text = help_text("Onde fica o Dashboard?", profile="FISCAL")
        self.assertIn("Menu → **Dashboard**", text)
