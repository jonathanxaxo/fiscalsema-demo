"""Sprint 49: qualquer perfil sai do sistema depois de 1 hora sem uso e entra de novo com a senha."""

import time
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountStatus, AuthenticationEvent, User
from contracts.tests import VALID_PASSWORD

KEY = "fiscalsema_ultima_atividade"


class SessaoInatividadeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="inativo@example.local", full_name="Fiscal Fictício",
                                             password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        self.client.force_login(self.user)

    def _idle(self, seconds):
        session = self.client.session
        session[KEY] = int(time.time()) - seconds
        session.save()

    def test_default_is_one_hour(self):
        from django.conf import settings
        self.assertEqual(settings.SESSION_IDLE_TIMEOUT_SECONDS, 3600)

    def test_activity_within_the_hour_keeps_the_session(self):
        self._idle(3500)
        page = self.client.get(reverse("home"))
        self.assertEqual(page.status_code, 200)
        self.assertGreater(self.client.session[KEY], int(time.time()) - 5)

    def test_more_than_one_hour_logs_out_and_asks_password(self):
        self._idle(3601)
        response = self.client.get(reverse("contracts:list"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(reverse("accounts:login") + "?next="))
        self.assertNotIn("_auth_user_id", self.client.session)
        login = self.client.get(response["Location"])
        self.assertContains(login, "Sua sessão foi encerrada após 1 hora sem uso")
        event = AuthenticationEvent.objects.filter(user=self.user, event_type=AuthenticationEvent.EventType.LOGOUT).get()
        self.assertEqual(event.details["motivo"], "inatividade")

    def test_chat_and_keepalive_get_json_401_after_timeout(self):
        self._idle(4000)
        response = self.client.get(reverse("accounts:session_keepalive"), HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(response.status_code, 401)
        self.assertIn("encerrada", response.json()["erro"])

    def test_keepalive_refreshes_activity_and_changes_no_data(self):
        self._idle(1800)
        response = self.client.get(reverse("accounts:session_keepalive"))
        self.assertEqual(response.status_code, 204)
        self.assertGreater(self.client.session[KEY], int(time.time()) - 5)

    def test_page_carries_timer_settings_for_logged_users_only(self):
        page = self.client.get(reverse("home"))
        self.assertContains(page, 'data-idle-timeout="3600"')
        self.assertContains(page, f'data-keepalive-url="{reverse("accounts:session_keepalive")}"')
        self.client.logout()
        self.assertNotContains(self.client.get(reverse("accounts:login")), "data-idle-timeout")

    @override_settings(SESSION_IDLE_TIMEOUT_SECONDS=0)
    def test_zero_disables(self):
        self._idle(999999)
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)


class SessaoFechaNavegadorTests(TestCase):
    """Sprint 51: fechar o navegador encerra o acesso (cookie de sessão sem validade)."""

    def test_setting_is_on_by_default(self):
        from django.conf import settings
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_login_cookie_has_no_expiry_date(self):
        from django.conf import settings
        User.objects.create_user(email="fecha@example.local", full_name="Fiscal Fictício",
                                 password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        response = self.client.post(reverse("accounts:login"), {"username": "fecha@example.local", "password": VALID_PASSWORD})
        self.assertEqual(response.status_code, 302)
        cookie = response.cookies[settings.SESSION_COOKIE_NAME]
        self.assertTrue(cookie.value)
        self.assertEqual(cookie["expires"], "")
        self.assertEqual(cookie["max-age"], "")
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_arise_knows_basic_rule_only(self):
        from assistant.conhecimento import help_text
        text = help_text("Se eu fechar o navegador ele desloga?", profile="FISCAL")
        self.assertIn("Ao fechar o sistema", text)
        self.assertIn("a aba dele ou o navegador inteiro", text)



class SessaoAbaFechadaTests(TestCase):
    """Sprint 52: fechou a aba do sistema e abriu de novo → pede a senha."""

    def setUp(self):
        self.user = User.objects.create_user(email="aba@example.local", full_name="Fiscal Fictício",
                                             password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        self.client.force_login(self.user)

    def test_pages_carry_tab_check_for_logged_users(self):
        page = self.client.get(reverse("home"))
        self.assertContains(page, f'data-tab-closed-url="{reverse("accounts:session_tab_closed")}"')
        self.assertContains(page, "sessionStorage.getItem('fiscalsema-aba')")
        self.client.logout()
        login = self.client.get(reverse("accounts:login"))
        self.assertNotContains(login, "data-tab-closed-url")
        self.assertNotContains(login, "fs-verificando")

    def test_closed_and_reopened_ends_session_with_audit_and_message(self):
        response = self.client.post(reverse("accounts:session_tab_closed"), HTTP_X_REQUESTED_WITH="fetch")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["login"], reverse("accounts:login"))
        self.assertNotIn("_auth_user_id", self.client.session)
        event = AuthenticationEvent.objects.get(user=self.user, event_type=AuthenticationEvent.EventType.LOGOUT)
        self.assertEqual(event.details["motivo"], "sistema fechado e reaberto")
        self.assertContains(self.client.get(reverse("accounts:login")), "o sistema foi fechado")

    def test_only_post_with_csrf(self):
        self.assertEqual(self.client.get(reverse("accounts:session_tab_closed")).status_code, 405)
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(reverse("accounts:session_tab_closed")).status_code, 403)
        self.assertIn("_auth_user_id", strict.session)
