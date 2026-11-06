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

from accounts.models import AccountStatus, AuthenticationEvent, ProfileSwitchLink, User, UserProfile
from accounts.profile_switch import SESSION_KEY
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

ADMIN_EMAIL = "admin@exemplo.com.br"


def enable(email=ADMIN_EMAIL, organization="SEMA", fiscal_name="Admin"):
    output = StringIO()
    env = {
        "DEMO_ADMIN_EMAIL": email,
        "DEMO_SWITCH_ORGANIZATION": organization,
        "DEMO_SWITCH_FISCAL_NAME": fiscal_name,
    }
    with mock.patch.dict(os.environ, env):
        call_command("enable_demo_profile_switch", stdout=output)
    return output.getvalue()


@override_settings(APP_ENVIRONMENT="demo")
class EnableProfileSwitchCommandTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email=ADMIN_EMAIL, full_name="Administrador Demonstração", password=VALID_PASSWORD
        )

    def test_creates_organization_fiscal_without_password_and_link(self):
        enable()
        link = ProfileSwitchLink.objects.select_related("fiscal__organization").get()
        self.assertEqual(link.administrator, self.admin)
        self.assertEqual(link.fiscal.profile, UserProfile.FISCAL)
        self.assertEqual(link.fiscal.full_name, "Admin")
        self.assertEqual(link.fiscal.organization.name, "SEMA")
        self.assertEqual(link.fiscal.status, AccountStatus.ACTIVE)
        self.assertFalse(link.fiscal.has_usable_password())
        self.assertFalse(link.fiscal.is_superuser)
        self.assertEqual(link.fiscal.email, "admin+fiscal@exemplo.com.br")
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                user=link.fiscal, event_type=AuthenticationEvent.EventType.FISCAL_CREATED
            ).exists()
        )
        self.assertEqual(
            User.objects.filter(profile=UserProfile.ADMINISTRATOR).count(), 1
        )

    def test_reuses_existing_organization_and_is_idempotent(self):
        Organization.objects.create(name="SEMA")
        enable()
        output = enable()
        self.assertIn("já habilitada", output)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(ProfileSwitchLink.objects.count(), 1)
        self.assertEqual(User.objects.count(), 2)

    def test_refuses_non_administrator_and_unknown_email(self):
        fiscal = User.objects.create_user(
            email="fiscal@exemplo.com.br",
            full_name="Fiscal",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.create(name="Outra"),
        )
        for email in (fiscal.email, "ninguem@exemplo.com.br"):
            with self.subTest(email=email), self.assertRaises(CommandError):
                enable(email=email)
        self.assertFalse(ProfileSwitchLink.objects.exists())

    def test_only_one_account_can_hold_the_exception(self):
        enable()
        other = User.objects.create_superuser(
            email="outro.admin@exemplo.com.br", full_name="Outro", password=VALID_PASSWORD
        )
        with self.assertRaises(CommandError):
            enable(email=other.email)
        self.assertEqual(ProfileSwitchLink.objects.count(), 1)

    @override_settings(APP_ENVIRONMENT="production")
    def test_refuses_outside_demo(self):
        with self.assertRaises(CommandError):
            enable()


@override_settings(APP_ENVIRONMENT="demo")
class ProfileSwitchFlowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email=ADMIN_EMAIL, full_name="Administrador Demonstração", password=VALID_PASSWORD
        )
        enable()
        self.fiscal = ProfileSwitchLink.objects.get().fiscal

    def login_admin(self):
        self.assertTrue(self.client.login(email=ADMIN_EMAIL, password=VALID_PASSWORD))

    def test_linked_admin_sees_switch_button(self):
        self.login_admin()
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Atuar como Fiscal")
        self.assertContains(response, reverse("accounts:switch_to_fiscal"))
        self.assertContains(response, 'class="sidebar-switch"')

    def test_switch_to_fiscal_and_back_with_audit(self):
        self.login_admin()
        response = self.client.post(reverse("accounts:switch_to_fiscal"))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(get_user(self.client), self.fiscal)
        self.assertEqual(self.client.session[SESSION_KEY], self.admin.pk)

        home = self.client.get(reverse("home"))
        self.assertContains(home, "Você está atuando como")
        self.assertContains(home, "Voltar a Administrador")
        self.assertEqual(self.client.get(reverse("contracts:create")).status_code, 200)
        self.assertNotEqual(self.client.get(reverse("accounts_admin:user_list")).status_code, 200)

        response = self.client.post(reverse("accounts:switch_to_administrator"))
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(get_user(self.client), self.admin)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(self.client.get(reverse("accounts_admin:user_list")).status_code, 200)

        events = list(
            AuthenticationEvent.objects.filter(user=self.admin)
            .filter(event_type__in=["PERFIL_FISCAL", "PERFIL_ADMIN"])
            .order_by("created_at", "pk")
            .values_list("event_type", flat=True)
        )
        self.assertEqual(events, ["PERFIL_FISCAL", "PERFIL_ADMIN"])

    def test_logout_and_login_again_returns_as_administrator(self):
        self.login_admin()
        self.client.post(reverse("accounts:switch_to_fiscal"))
        self.client.post(reverse("accounts:logout"))
        self.login_admin()
        self.assertEqual(get_user(self.client), self.admin)
        self.assertContains(self.client.get(reverse("home")), "Atuar como Fiscal")

    def test_switch_requires_post(self):
        self.login_admin()
        self.assertEqual(self.client.get(reverse("accounts:switch_to_fiscal")).status_code, 405)

    def test_other_accounts_cannot_switch(self):
        other_admin = User.objects.create_superuser(
            email="outro.admin@exemplo.com.br", full_name="Outro", password=VALID_PASSWORD
        )
        regular_fiscal = User.objects.create_user(
            email="fiscal@exemplo.com.br",
            full_name="Fiscal Comum",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.get(name="SEMA"),
        )
        self.client.force_login(other_admin)
        self.assertNotContains(self.client.get(reverse("home")), "Atuar como Fiscal")
        self.assertEqual(self.client.post(reverse("accounts:switch_to_fiscal")).status_code, 403)
        self.assertEqual(get_user(self.client), other_admin)

        self.client.force_login(regular_fiscal)
        session = self.client.session
        session[SESSION_KEY] = self.admin.pk
        session.save()
        self.assertEqual(
            self.client.post(reverse("accounts:switch_to_administrator")).status_code, 403
        )
        self.assertEqual(get_user(self.client), regular_fiscal)

    def test_linked_fiscal_cannot_log_in_with_password(self):
        self.assertFalse(self.client.login(email=self.fiscal.email, password=""))
        self.assertFalse(self.client.login(email=self.fiscal.email, password=VALID_PASSWORD))

    def test_inactive_administrator_cannot_switch(self):
        self.login_admin()
        User.objects.filter(pk=self.admin.pk).update(status=AccountStatus.BLOCKED, is_active=False)
        response = self.client.post(reverse("accounts:switch_to_fiscal"))
        self.assertNotEqual(get_user(self.client), self.fiscal)
        self.assertIn(response.status_code, {302, 403})


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
