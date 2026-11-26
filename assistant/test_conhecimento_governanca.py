"""Conhecimento seguro do Arise sobre as Sprints 63 a 69."""

from django.test import SimpleTestCase

from assistant.conhecimento import help_text, select_sections


class ConhecimentoGovernancaTests(SimpleTestCase):
    def test_governance_questions_find_the_new_section(self):
        questions = (
            "Onde acompanho aditivo, apostilamento e prorrogação?",
            "Como funciona o checklist de contrato de TIC?",
            "O sistema integra automaticamente com SIAG, SIGADOC e PNCP?",
        )
        for question in questions:
            for profile in (
                "FISCAL_TITULAR",
                "AUXILIAR_ADMINISTRATIVA",
                "GESTOR_ADMINISTRATIVO",
                "GESTOR_DO_CONTRATO",
            ):
                names = [item.name for item in select_sections(question, profile=profile)]
                self.assertIn("20-governanca-contratual", names[:3])

    def test_help_preserves_human_confirmation_and_manual_external_tracking(self):
        text = help_text(
            "O checklist cria obrigação e atualiza o SIAG sozinho?",
            profile="FISCAL_TITULAR",
        )
        self.assertIn("A confirmar na fonte oficial", text)
        self.assertIn("não viram obrigação automaticamente", text)
        self.assertIn("controle manual", text)
        self.assertIn("não acessa nem atualiza", text)
