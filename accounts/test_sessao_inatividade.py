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
