"""Sprint 74: perguntas sugeridas sobre o contrato ativo e relatórios revisados."""

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.test import SimpleTestCase

from .conhecimento import CONTRACT_SUGGESTIONS, SUGGESTIONS, contract_suggestions_for, suggestions_for


def static_text(path):
    with open(finders.find(path), encoding="utf-8") as arquivo:
        return arquivo.read()


class SugestoesContratoTests(SimpleTestCase):
    def test_without_contract_keeps_profile_suggestions(self):
        for perfil, sugestoes in SUGGESTIONS.items():
            self.assertEqual(suggestions_for(perfil), sugestoes)

    def test_with_contract_uses_contract_questions(self):
        contrato = object()
        self.assertIn("Qual é o saldo deste contrato?", suggestions_for("FISCAL_TITULAR", contract=contrato))
        self.assertIn("Existem notas fiscais pendentes?", contract_suggestions_for("GESTOR_DO_CONTRATO"))
        self.assertIn("Quais empenhos estão associados?", contract_suggestions_for("FISCAL"))

    def test_auxiliary_never_gets_value_questions(self):
        auxiliar = contract_suggestions_for("AUXILIAR_ADMINISTRATIVA")
        self.assertTrue(auxiliar)
        for pergunta in auxiliar:
            for termo in ("saldo", "empenho", "nota fiscal", "notas fiscais", "valor", "pago"):
                self.assertNotIn(termo, pergunta.lower())

    def test_profile_without_contract_questions_falls_back(self):
        self.assertNotIn("ADMINISTRADOR_GERAL", CONTRACT_SUGGESTIONS)
        self.assertEqual(contract_suggestions_for("ADMINISTRADOR_GERAL"), SUGGESTIONS["ADMINISTRADOR_GERAL"])

    def test_active_contract_badge_is_highlighted(self):
        css = static_text("assistant/chat.css")
        self.assertIn(".assistant-contract-context.is-selected { border-left: 4px solid var(--green-700); }", css)


class RelatoriosImpressaoTests(SimpleTestCase):
    def test_wide_report_tables_print_whole_without_scroll_hint(self):
        css = static_text("core/css/app.css")
        for regra in (
            "main.report-page .table-scroll-hint, main.report-page .table-scroll-hint.is-visible { display: none; }",
            "main.report-page .table-responsive { overflow: visible; max-width: none; }",
            "main.report-page thead { display: table-header-group; }",
        ):
            self.assertIn(regra, css)

    def test_management_report_no_longer_mentions_fictitious_data(self):
        caminho = Path(settings.BASE_DIR, "templates", "contracts", "administrative_portfolio_report.html")
        with open(caminho, encoding="utf-8") as arquivo:
            html = arquivo.read()
        self.assertNotIn("dados fictícios", html)
        self.assertIn("Não constitui atesto, homologação, liquidação, autorização nem recomendação de pagamento.", html)
