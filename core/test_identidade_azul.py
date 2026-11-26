"""Sprint 72: identidade azul e branco, novo logotipo e marca institucional inteira."""

import struct

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountStatus
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

PALETA = {
    "--green-950": "#092b55",  # azul profundo (nome histórico da variável)
    "--green-800": "#083b8a",  # azul escuro
    "--green-700": "#0b5ed7",  # azul principal
    "--green-50": "#eaf3ff",  # azul claro
    "--canvas": "#f5f8fc",  # fundo
    "--ink": "#1f2d3d",  # texto
}
VERDES_ANTIGOS = ("#0b5d3b", "#103c2c", "#147447", "#0a4a30", "#44dc9c", "#2fc589")


def static_text(path):
    with open(finders.find(path), encoding="utf-8") as arquivo:
        return arquivo.read()


class PaletaAzulTests(TestCase):
    def test_css_uses_blue_palette_from_master_prompt(self):
        css = static_text("core/css/app.css")
        for variavel, valor in PALETA.items():
            self.assertIn(f"{variavel}: {valor}", css)
        for arquivo in ("core/css/app.css", "assistant/chat.css"):
            texto = static_text(arquivo).lower()
            for verde in VERDES_ANTIGOS:
                self.assertNotIn(verde, texto, f"{verde} ainda em {arquivo}")

    def test_success_and_alert_colors_are_preserved(self):
        css = static_text("core/css/app.css")
        self.assertIn("--success-bg: #e3f4e9", css)
        self.assertIn(".status-success { background: var(--success-bg); color: var(--success-ink); }", css)
        self.assertIn("--danger-bg: #fff0ef", css)
        self.assertIn("--warning-bg: #fff7df", css)

    def test_theme_color_is_blue(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, '<meta name="theme-color" content="#083b8a">', html=False)


class LogotipoAzulTests(TestCase):
    def test_logo_has_document_magnifier_and_check_in_blue_and_white(self):
        for arquivo in ("core/img/logo.svg", "core/img/logo-estatico.svg", "core/img/favicon.svg"):
            svg = static_text(arquivo)
            self.assertIn("#0b5ed7", svg)  # azul principal
            self.assertIn('fill="#fff"', svg)  # documento branco
            self.assertIn("M10 5h14.5l7.5 7.5", svg)  # folha com canto dobrado
            self.assertIn('d="M15.5 21.5l4 4 7.5-8"', svg)  # verificação
            self.assertIn('d="M30 30l9 9"', svg)  # cabo da lupa
            for verde in VERDES_ANTIGOS:
                self.assertNotIn(verde, svg)

    def test_scan_animation_kept_only_in_live_version(self):
        self.assertIn('class="scan"', static_text("core/img/logo.svg"))
        self.assertNotIn("animation", static_text("core/img/logo-estatico.svg"))
        self.assertNotIn("animation", static_text("core/img/favicon.svg"))


class MarcaInstitucionalTests(TestCase):
    ALT = "SEMA — Secretaria de Estado de Meio Ambiente · Brasão e Governo de Mato Grosso"

    def test_institutional_image_is_whole_and_proportional(self):
        caminho = finders.find("core/img/sema-governo-mt.png")
        self.assertIsNotNone(caminho)
        with open(caminho, "rb") as arquivo:
            cabecalho = arquivo.read(26)
        self.assertEqual(cabecalho[:8], b"\x89PNG\r\n\x1a\n")
        largura, altura = struct.unpack(">II", cabecalho[16:24])
        self.assertEqual((largura, altura), (1698, 543))  # tamanho original, sem recorte
        self.assertEqual(cabecalho[25], 6)  # RGBA: fundo transparente
        css = static_text("core/css/app.css")
        self.assertIn(".institutional-mark { display: block; max-width: 100%; height: auto; }", css)
        self.assertNotIn("institutional-mark { object-fit", css)

    def test_login_shows_institutional_image_below_form(self):
        response = self.client.get(reverse("accounts:login"))
        html = response.content.decode()
        self.assertContains(response, "core/img/sema-governo-mt.png")
        self.assertContains(response, self.ALT)
        self.assertContains(response, "Fiscalização de contratos")
        self.assertLess(html.index('class="auth-card"'), html.index("sema-governo-mt.png"))
        self.assertContains(response, "Entrar com Google")
        self.assertContains(response, "Esqueci minha senha")

    def test_internal_pages_have_institutional_footer_with_demo_notice(self):
        user = get_user_model().objects.create_user(
            email="azul@example.local",
            full_name="Fiscal Azul",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.create(name="DEMO"),
        )
        self.client.force_login(user)
        for rota in ("home", "contracts:list", "methodology"):
            response = self.client.get(reverse(rota))
            self.assertContains(response, 'class="app-footer"')
            self.assertContains(response, self.ALT)
            self.assertContains(response, "Fiscalização de contratos")
            # Sprint 72: sem faixa nem notas de dados fictícios nas telas (aviso no vídeo).
            for aviso in ("AMBIENTE DE DEMONSTRAÇÃO", "Não inserir dados ou documentos reais", "Ambiente de demonstração com dados fictícios"):
                self.assertNotContains(response, aviso)
        resposta = self.client.get(reverse("home"))
        self.assertContains(resposta, '<span class="badge badge-profile">', html=False)
        self.assertNotContains(resposta, '<span class="badge badge-success">Fiscal', html=False)

    def test_login_has_no_demo_notice(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertNotContains(response, "AMBIENTE DE DEMONSTRAÇÃO")
        self.assertNotContains(response, "Ambiente de demonstração · dados fictícios")

    def test_profile_badge_is_light_blue(self):
        self.assertIn(".badge-profile { background: #dbeafe; color: #083b8a;", static_text("core/css/app.css"))

    def test_footer_is_hidden_when_printing_reports(self):
        self.assertIn("@media print { .app-footer { display: none; } }", static_text("core/css/app.css"))
