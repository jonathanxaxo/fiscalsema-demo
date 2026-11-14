"""E-mail de redefinição de senha e senha temporária da demo (Sprint 26)."""

import os
from io import StringIO
from unittest import mock

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountStatus, AuthenticationEvent, LoginThrottle, User
from accounts.services import record_login_failure
from contracts.tests import VALID_PASSWORD
from core.email_config import email_settings

TEMP = "Temporaria!2026xy"


class EmailRedefinicaoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="fiscal.email@example.local", full_name="Fiscal Email", password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )

    def test_reset_email_is_sent_with_link_and_clear_text(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": self.user.email})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "Redefinição de senha — FiscalSema")
        self.assertEqual(message.to, [self.user.email])
        self.assertIn("/conta/redefinir-senha/", message.body)
        self.assertIn("Olá, Fiscal.", message.body)
        self.assertIn("ignore esta mensagem", message.body)
        self.assertNotIn("Light", message.body + message.subject)

    def test_unknown_email_sends_nothing_but_same_page(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "ninguem@example.local"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)


class ConfiguracaoEmailTests(TestCase):
    def test_without_credentials_email_stays_fictitious(self):
        config = email_settings({})
        self.assertEqual(config["EMAIL_BACKEND"], "django.core.mail.backends.dummy.EmailBackend")

    def test_with_credentials_uses_smtp_tls(self):
        config = email_settings({"EMAIL_HOST_USER": "remetente@example.local", "EMAIL_HOST_PASSWORD": "app-ficticia"})
        self.assertEqual(config["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertEqual((config["EMAIL_HOST"], config["EMAIL_PORT"], config["EMAIL_USE_TLS"]), ("smtp.gmail.com", 587, True))
        self.assertEqual(config["DEFAULT_FROM_EMAIL"], "FiscalSema Demo <remetente@example.local>")

    def test_demo_settings_use_the_helper(self):
        from pathlib import Path

        from django.conf import settings
        source = Path(settings.BASE_DIR, "core", "settings_demo.py").read_text(encoding="utf-8")
        self.assertIn("globals().update(email_settings(os.environ))", source)
        self.assertNotIn('EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"', source)


@override_settings(APP_ENVIRONMENT="demo")
class SenhaTemporariaTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="esqueci@example.local", full_name="Conta Esquecida", password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )

    def run_command(self, email="esqueci@example.local", password=TEMP):
        with mock.patch.dict(os.environ, {"DEMO_RESET_EMAIL": email, "DEMO_TEMP_PASSWORD": password}):
            call_command("set_demo_temporary_password", stdout=StringIO())

    def test_sets_temporary_password_and_forces_change(self):
        for _ in range(5):
            record_login_failure(self.user.email)
        before = (self.user.profile, self.user.status, self.user.organization_id)
        self.run_command(email="ESQUECI@example.local")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(TEMP))
        self.assertTrue(self.user.must_change_password)
        self.assertEqual((self.user.profile, self.user.status, self.user.organization_id), before)
        self.assertFalse(LoginThrottle.objects.exists())
        event = AuthenticationEvent.objects.get(user=self.user, event_type="SENHA_ALTERADA")
        self.assertEqual(event.details["origem"], "fluxo_manual_senha_temporaria")
        self.assertNotIn(TEMP, str(event.details))

    def test_login_with_temporary_password_requires_new_password(self):
        self.run_command()
        self.client.post(reverse("accounts:login"), {"username": self.user.email, "password": TEMP})
        response = self.client.get(reverse("home"))
        self.assertRedirects(response, reverse("accounts:password_change"), fetch_redirect_response=False)

    def test_refusals(self):
        with self.assertRaises(CommandError):
            self.run_command(email="nao-existe@example.local")
        with self.assertRaises(CommandError):
            self.run_command(password="123")
        with override_settings(APP_ENVIRONMENT="development"):
            with self.assertRaises(CommandError):
                self.run_command()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(VALID_PASSWORD))
