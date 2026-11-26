from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from accounts.models import AccountStatus


class BaseTecnicaTests(TestCase):
    def test_home(self):
        response = Client().get("/")
        self.assertRedirects(response, "/conta/entrar/?next=/")

    def test_home_autenticada(self):
        user = get_user_model().objects.create_user(
            email="fiscal.base@example.local",
            full_name="Fiscal de Teste",
            password="SenhaMuitoForte!2026",
            status=AccountStatus.ACTIVE,
        )
        client = Client()
        client.force_login(user)
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fiscal de Teste")
        self.assertContains(response, 'id="menu-principal"')
        self.assertContains(response, "Rascunhos da IA")
        # Sprint 72: por decisão do responsável, o aviso é feito na apresentação e no vídeo.
        self.assertNotContains(response, "AMBIENTE DE DEMONSTRAÇÃO")
        self.assertNotContains(response, "DADOS EXCLUSIVAMENTE FICTÍCIOS")
        self.assertNotContains(response, "Ambiente interno")

    def test_layout_publico_tem_identidade_e_acessibilidade(self):
        response = Client().get("/conta/entrar/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fiscalização de contratos")
        self.assertContains(response, 'class="skip-link"')
        self.assertContains(response, "/static/core/css/app.css")
        self.assertContains(response, "/static/core/js/app.js")

    @override_settings(APP_ENVIRONMENT="homologation")
    def test_homologacao_e_identificada_visualmente(self):
        response = Client().get("/conta/entrar/")
        self.assertContains(response, "AMBIENTE DE HOMOLOGAÇÃO")
        self.assertContains(response, "não utilizar para operação real")
        self.assertContains(response, 'class="environment-banner"')

    @override_settings(APP_ENVIRONMENT="production")
    def test_producao_nao_exibe_identificacao_de_homologacao(self):
        response = Client().get("/conta/entrar/")
        self.assertNotContains(response, "AMBIENTE DE HOMOLOGAÇÃO")

    def test_health(self):
        response = Client().get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_producao_nao_habilita_debug(self):
        self.assertFalse(settings.DEBUG)

    def test_postgresql_e_banco_configurado(self):
        database = settings.DATABASES["default"]
        self.assertEqual(database["ENGINE"], "django.db.backends.postgresql")
        self.assertTrue(database["NAME"])

    def test_cabecalhos_de_seguranca(self):
        response = Client().get("/")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")

    def test_cookie_de_sessao_tem_configuracao_segura(self):
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
