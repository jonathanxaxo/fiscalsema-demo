import os
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AccountStatus, AuthenticationEvent, ProfileSwitchLink, User
from accounts.profile_switch import SESSION_KEY
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

FISCAL_EMAIL = "admin@exemplo.com.br"
ADMIN_EMAIL = "administrador.inicial@exemplo.local"
SWITCH_URL = "accounts:switch_profile"


def enable(fiscal_email=FISCAL_EMAIL, admin_email=""):
    output = StringIO()
    env = {"DEMO_SWITCH_FISCAL_EMAIL": fiscal_email, "DEMO_SWITCH_ADMIN_EMAIL": admin_email}
    with mock.patch.dict(os.environ, env):
        call_command("enable_demo_profile_switch", stdout=output)
    return output.getvalue()


class ProfileSwitchBase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SEMA")
        self.admin = User.objects.create_superuser(
            email=ADMIN_EMAIL, full_name="Administrador Inicial", password=VALID_PASSWORD
        )
        self.fiscal = User.objects.create_user(
            email=FISCAL_EMAIL,
            full_name="Admin",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )

    def other_fiscal(self):
        return User.objects.create_user(
            email="fiscal.comum@exemplo.com.br",
            full_name="Fiscal Comum",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )


@override_settings(APP_ENVIRONMENT="demo")
class EnableProfileSwitchCommandTests(ProfileSwitchBase):
    def test_links_fiscal_to_the_single_administrator_without_creating_accounts(self):
        users_before = User.objects.count()
        enable()
        link = ProfileSwitchLink.objects.get()
        self.assertEqual(link.fiscal, self.fiscal)
        self.assertEqual(link.administrator, self.admin)
        self.assertEqual(User.objects.count(), users_before)
        self.fiscal.refresh_from_db()
        self.assertTrue(self.fiscal.check_password(VALID_PASSWORD))

    def test_is_idempotent(self):
        enable()
        self.assertIn("já habilitada", enable())
        self.assertEqual(ProfileSwitchLink.objects.count(), 1)

    def test_refuses_accounts_that_are_not_active_fiscal(self):
        for email in (ADMIN_EMAIL, "ninguem@exemplo.com.br"):
            with self.subTest(email=email), self.assertRaises(CommandError):
                enable(fiscal_email=email)
        self.assertFalse(ProfileSwitchLink.objects.exists())

    def test_requires_exactly_one_administrator_when_not_informed(self):
        User.objects.create_superuser(
            email="segundo.admin@exemplo.local", full_name="Segundo", password=VALID_PASSWORD
        )
        with self.assertRaises(CommandError):
            enable()
        enable(admin_email=ADMIN_EMAIL)
        self.assertEqual(ProfileSwitchLink.objects.get().administrator, self.admin)

    def test_only_one_account_can_hold_the_exception(self):
        enable()
        with self.assertRaises(CommandError):
            enable(fiscal_email=self.other_fiscal().email)
        self.assertEqual(ProfileSwitchLink.objects.count(), 1)

    @override_settings(APP_ENVIRONMENT="production")
    def test_refuses_outside_demo(self):
        with self.assertRaises(CommandError):
            enable()


@override_settings(APP_ENVIRONMENT="demo")
class ProfileSwitchFlowTests(ProfileSwitchBase):
    def setUp(self):
        super().setUp()
        enable()

    def login_fiscal(self):
        self.assertTrue(self.client.login(email=FISCAL_EMAIL, password=VALID_PASSWORD))

    def test_fiscal_sees_switch_to_administrator(self):
        self.login_fiscal()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Atuar como Administrador")
        self.assertContains(response, 'class="sidebar-switch"')

    def test_switch_to_administrator_and_back_with_audit(self):
        self.login_fiscal()
        self.assertEqual(self.client.get(reverse("accounts_admin:user_list")).status_code, 403)

        response = self.client.post(reverse(SWITCH_URL))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(get_user(self.client), self.admin)
        self.assertEqual(self.client.session[SESSION_KEY], self.fiscal.pk)
        home = self.client.get(reverse("home"))
        self.assertContains(
            home,
            "Você está atuando como <strong>Administrador Geral</strong>",
            html=False,
        )
        self.assertContains(home, "Voltar a Fiscal")
        self.assertEqual(self.client.get(reverse("accounts_admin:user_list")).status_code, 200)

        self.client.post(reverse(SWITCH_URL))
        self.assertEqual(get_user(self.client), self.fiscal)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(self.client.get(reverse("home")), "Atuar como Administrador")
        self.assertEqual(self.client.get(reverse("contracts:create")).status_code, 200)

        events = list(
            AuthenticationEvent.objects.filter(user=self.fiscal)
            .filter(event_type__in=["PERFIL_FISCAL", "PERFIL_ADMIN"])
            .order_by("created_at", "pk")
            .values_list("event_type", flat=True)
        )
        self.assertEqual(events, ["PERFIL_ADMIN", "PERFIL_FISCAL"])

    def test_logout_and_login_again_starts_as_fiscal(self):
        self.login_fiscal()
        self.client.post(reverse(SWITCH_URL))
        self.client.post(reverse("accounts:logout"))
        self.login_fiscal()
        self.assertEqual(get_user(self.client), self.fiscal)

    def test_switch_requires_post(self):
        self.login_fiscal()
        self.assertEqual(self.client.get(reverse(SWITCH_URL)).status_code, 405)

    def test_other_accounts_cannot_switch(self):
        regular = self.other_fiscal()
        self.client.force_login(regular)
        self.assertNotContains(self.client.get(reverse("home")), "Atuar como")
        self.assertEqual(self.client.post(reverse(SWITCH_URL)).status_code, 403)
        self.assertEqual(get_user(self.client), regular)

        session = self.client.session
        session[SESSION_KEY] = self.fiscal.pk
        session.save()
        self.assertEqual(self.client.post(reverse(SWITCH_URL)).status_code, 403)
        self.assertEqual(get_user(self.client), regular)

    def test_inactive_target_cannot_be_used(self):
        self.login_fiscal()
        User.objects.filter(pk=self.admin.pk).update(status=AccountStatus.BLOCKED, is_active=False)
        self.assertEqual(self.client.post(reverse(SWITCH_URL)).status_code, 403)
        self.assertEqual(get_user(self.client), self.fiscal)


class EnableProfileSwitchWorkflowTests(TestCase):
    def test_workflow_is_manual_confirmed_and_checks_migrations(self):
        workflow = (
            Path(settings.BASE_DIR) / ".github" / "workflows" / "enable-demo-profile-switch.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertIn('test "$CONFIRMACAO" = "HABILITAR"', workflow)
        self.assertIn("python manage.py migrate --check", workflow)
        self.assertIn("python manage.py enable_demo_profile_switch", workflow)
