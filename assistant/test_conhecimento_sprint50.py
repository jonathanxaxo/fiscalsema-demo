"""Sprint 50: o Arise conhece as novidades das Sprints 41 a 49 só no nível de uso básico,
sem detalhes internos que possam prejudicar a segurança."""

import re

from django.test import SimpleTestCase

from assistant.conhecimento import BASE_DIR, help_text, select_sections
from assistant.prompt import RULES, build_messages

# Termos técnicos que não podem aparecer na ajuda enviada à IA.
PROIBIDOS = re.compile(
    r"SESSION_|middleware|settings|sessao/ativa|keepalive|\.env\b|cookie|csrf|token|secret|api[_ ]?key|"
    r"DATABASE|postgres|hmac|hash|localStorage|data-idle|X-Requested",
    re.IGNORECASE,
)


class ConhecimentoNovidadesTests(SimpleTestCase):
    CASES = {
        "Como arrasto e minimizo o chat flutuante?": "16-chat-arise",
        "O aviso amarelo do chat some sozinho?": "16-chat-arise",
        "Preciso clicar no botão abrir para ver a OS na lista?": "17-listas-e-os",
        "Onde fica o botão cadastrar nota fiscal na OS?": "17-listas-e-os",
        "Como deixo o sistema sem animação, parado?": "18-visual-movimento",
        "Por que a lupa do logotipo está parada?": "18-visual-movimento",
        "Por que o sistema me deslogou e pediu a senha de novo?": "19-sessao-seguranca",
        "Depois de quanto tempo sem uso a sessão expira?": "19-sessao-seguranca",
        "Qual o tempo de ociosidade do sistema?": "19-sessao-seguranca",
    }

    def test_each_novelty_finds_its_help_section(self):
        for question, section in self.CASES.items():
            for profile in ("FISCAL", "ADMINISTRADOR", "USUARIO_CONSULTA"):
                names = [item.name for item in select_sections(question, profile=profile)]
                self.assertIn(section, names[:3], f"{question} ({profile})")

    def test_basic_answers_are_in_the_help(self):
        self.assertIn("1 hora sem usar", help_text("Por que fui deslogado?", profile="FISCAL"))
        self.assertIn("10 segundos", help_text("O aviso amarelo do chat some?", profile="FISCAL"))
        self.assertIn("Ctrl", help_text("Como abrir a linha em nova aba?", profile="FISCAL"))

    def test_idle_time_is_always_known(self):
        for question in ("Oi, tudo bem?", "Como cadastro um contrato?", "Qual o tempo de ociosidade?"):
            self.assertIn("1 hora sem usar o sistema", help_text(question, profile="USUARIO_CONSULTA"))

    def test_no_internal_detail_in_any_help_file(self):
        for path in sorted(BASE_DIR.glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("palavras:"):
                    continue
                self.assertIsNone(PROIBIDOS.search(line), f"{path.name}: {line}")

    def test_session_help_does_not_teach_how_to_extend_or_bypass(self):
        text = help_text("Como aumentar o tempo da sessão ou evitar sair?", profile="FISCAL").lower()
        self.assertIn("não pode ser alterado pelo usuário", text)
        for termo in ("variável", "configuração", "segundos de", "desativar", "desligar o tempo"):
            self.assertNotIn(termo, text)

    def test_security_rule_in_system_prompt(self):
        self.assertIn("11. Segurança do sistema", RULES)
        for piece in ("Nunca informe detalhes técnicos internos", "burlar, desligar, prolongar ou contornar",
                      "indique o Administrador"):
            self.assertIn(piece, RULES)
        system = build_messages("Qual variável muda o tempo de sessão?", profile="FISCAL")[0]["content"]
        self.assertIn("11. Segurança do sistema", system)
        self.assertIsNone(PROIBIDOS.search(system.split("<ajuda>\n", 1)[1].split("</ajuda>", 1)[0]))
