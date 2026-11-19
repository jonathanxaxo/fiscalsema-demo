import os
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

from .models import (
    DEMO_SWITCH_PROFILES,
    AccountStatus,
    AuthenticationEvent,
    DemoProfileSwitch,
    DemoProfileSwitchTarget,
    User,
    UserProfile,
)
from .profile_switch import SESSION_KEY
from .services import change_user_profile, change_user_status

CONTROLLER_EMAIL = "admin@exemplo.com.br"


def enable_multprofile(email=CONTROLLER_EMAIL):
    output = StringIO()
    with mock.patch.dict(os.environ, {"DEMO_SWITCH_CONTROLLER_EMAIL": email}):
        call_command("enable_demo_multprofile_switch", stdout=output)
    return output.getvalue()


@override_settings(APP_ENVIRONMENT="demo")
class DemoMultiProfileTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SEMA")
        self.administrator = User.objects.create_superuser(
            email="administrador.inicial@exemplo.local",
            full_name="Administrador Inicial",
            password=VALID_PASSWORD,
        )
        self.controller = User.objects.create_user(
            email=CONTROLLER_EMAIL,
            full_name="Responsável pela demonstração",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )

    def test_command_creates_five_targets_without_changing_controller_password(self):
        output = enable_multprofile()
        switch = DemoProfileSwitch.objects.get(controller=self.controller)
        self.assertEqual(
            set(switch.targets.values_list("profile", flat=True)),
            set(DEMO_SWITCH_PROFILES),
        )
        self.assertEqual(switch.targets.count(), 5)
        self.assertIn("5 perfis", output)
        self.controller.refresh_from_db()
        self.assertTrue(self.controller.check_password(VALID_PASSWORD))
        internal = switch.targets.filter(is_internal=True).select_related("user")
        self.assertEqual(internal.count(), 3)
        self.assertTrue(all(not item.user.has_usable_password() for item in internal))

    def test_command_is_idempotent_and_refuses_another_controller(self):
        enable_multprofile()
        users_before = User.objects.count()
        enable_multprofile()
        self.assertEqual(User.objects.count(), users_before)
        other = User.objects.create_user(
            email="outro.fiscal@exemplo.com.br",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        with self.assertRaises(CommandError):
            enable_multprofile(other.email)
        self.assertEqual(DemoProfileSwitch.objects.get().controller, self.controller)

    def test_controller_switches_directly_between_all_profiles_and_back(self):
        enable_multprofile()
        self.assertTrue(
            self.client.login(email=CONTROLLER_EMAIL, password=VALID_PASSWORD)
        )
        home = self.client.get(reverse("home"))
        self.assertContains(home, "Trocar perfil")
        for profile in (
            UserProfile.ADMINISTRATOR_GENERAL,
            UserProfile.AUXILIARY_ADMINISTRATIVE,
            UserProfile.ADMINISTRATIVE_MANAGER,
            UserProfile.CONTRACT_MANAGER,
            UserProfile.FISCAL_TITULAR,
        ):
            response = self.client.post(
                reverse("accounts:switch_profile"),
                {"profile": profile},
            )
            self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
            self.assertEqual(get_user(self.client).profile, profile)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(
            AuthenticationEvent.objects.filter(
                user=self.controller,
                event_type=AuthenticationEvent.EventType.PROFILE_SWITCHED,
            ).count(),
            5,
        )

    def test_only_controller_can_start_switch_and_internal_accounts_cannot_login(self):
        enable_multprofile()
        self.client.force_login(self.administrator)
        self.assertNotContains(self.client.get(reverse("home")), "Trocar perfil")
        self.assertEqual(
            self.client.post(
                reverse("accounts:switch_profile"),
                {"profile": UserProfile.FISCAL_TITULAR},
            ).status_code,
            403,
        )
        self.client.logout()
        for target in DemoProfileSwitchTarget.objects.filter(
            is_internal=True
        ).select_related("user"):
            self.assertFalse(
                self.client.login(email=target.user.email, password=VALID_PASSWORD)
            )

    def test_internal_accounts_are_hidden_from_regular_user_management(self):
        enable_multprofile()
        self.client.force_login(self.controller)
        self.client.post(
            reverse("accounts:switch_profile"),
            {"profile": UserProfile.ADMINISTRATOR_GENERAL},
        )
        response = self.client.get(reverse("accounts_admin:user_list"))
        self.assertEqual(response.status_code, 200)
        for target in DemoProfileSwitchTarget.objects.filter(
            is_internal=True
        ).select_related("user"):
            self.assertNotContains(response, target.user.email)

    def test_internal_accounts_cannot_be_changed_by_regular_admin_flows(self):
        enable_multprofile()
        internal = DemoProfileSwitchTarget.objects.select_related("user").filter(
            is_internal=True
        ).first().user
        with self.assertRaisesMessage(ValidationError, "Conta interna"):
            change_user_status(
                user_id=internal.pk,
                actor=self.administrator,
                action="deactivate",
            )
        with self.assertRaisesMessage(ValidationError, "Conta interna"):
            change_user_profile(
                user_id=internal.pk,
                actor=self.administrator,
                profile=UserProfile.FISCAL_TITULAR,
            )
        internal.refresh_from_db()
        self.assertEqual(internal.status, AccountStatus.ACTIVE)
        self.assertFalse(internal.has_usable_password())

    @override_settings(APP_ENVIRONMENT="production")
    def test_command_refuses_outside_demo(self):
        with self.assertRaises(CommandError):
            enable_multprofile()


class PrepareDemoWorkflowTests(TestCase):
    def test_workflow_is_manual_confirmed_and_does_not_deploy(self):
        workflow = (
            Path(settings.BASE_DIR)
            / ".github"
            / "workflows"
            / "prepare-demo-multprofile.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn('test "$CONFIRMACAO" = "PREPARAR DEMO"', workflow)
        self.assertIn("python manage.py migrate --check", workflow)
        self.assertIn("python manage.py enable_demo_multprofile_switch", workflow)
        self.assertIn("python manage.py seed_demo_portfolio", workflow)
        self.assertNotIn("vercel deploy", workflow.casefold())
        self.assertNotIn("vercel-action", workflow.casefold())
        self.assertNotIn("push:", workflow)
