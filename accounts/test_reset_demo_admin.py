import os
from io import StringIO
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from accounts.models import AccountStatus, AuthenticationEvent, User
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

NEW_PASSWORD = "NovaSenhaFicticia!2026"


@override_settings(APP_ENVIRONMENT="demo")
class ResetDemoAdminPasswordTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@exemplo.local",
            full_name="Administrador Demonstração",
            password=VALID_PASSWORD,
        )

    def run_command(self, email, password):
        output = StringIO()
        with mock.patch.dict(os.environ, {"DEMO_ADMIN_EMAIL": email, "DEMO_ADMIN_PASSWORD": password}):
            call_command("reset_demo_admin_password", stdout=output)
        return output.getvalue()

    def test_resets_password_keeping_login_and_records_audit_event(self):
        output = self.run_command("ADMIN@exemplo.local", NEW_PASSWORD)
        self.assertIsNone(authenticate(email="admin@exemplo.local", password=VALID_PASSWORD))
        self.assertEqual(authenticate(email="admin@exemplo.local", password=NEW_PASSWORD), self.admin)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, "admin@exemplo.local")
        self.assertFalse(self.admin.must_change_password)
        event = AuthenticationEvent.objects.get(
            user=self.admin, event_type=AuthenticationEvent.EventType.PASSWORD_CHANGED
        )
        self.assertEqual(event.details["origem"], "reset_demo_admin_password_env")
        self.assertNotIn(NEW_PASSWORD, output)
        self.assertNotIn(NEW_PASSWORD, str(event.details))
        self.assertEqual(User.objects.count(), 1)

    def test_refuses_unknown_email_without_changing_anything(self):
        with self.assertRaises(CommandError):
            self.run_command("outro@exemplo.local", NEW_PASSWORD)
        self.assertEqual(authenticate(email="admin@exemplo.local", password=VALID_PASSWORD), self.admin)
        self.assertEqual(User.objects.count(), 1)

    def test_refuses_fiscal_accounts(self):
        fiscal = User.objects.create_user(
            email="fiscal@exemplo.local",
            full_name="Fiscal Fictício",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.create(name="DEMO"),
        )
        with self.assertRaises(CommandError):
            self.run_command(fiscal.email, NEW_PASSWORD)
        self.assertEqual(authenticate(email=fiscal.email, password=VALID_PASSWORD), fiscal)

    def test_refuses_weak_password(self):
        with self.assertRaises(Exception):
            self.run_command("admin@exemplo.local", "123")
        self.assertEqual(authenticate(email="admin@exemplo.local", password=VALID_PASSWORD), self.admin)

    def test_refuses_missing_variables(self):
        with self.assertRaises(CommandError):
            self.run_command("", NEW_PASSWORD)
        with self.assertRaises(CommandError):
            self.run_command("admin@exemplo.local", "")

    @override_settings(APP_ENVIRONMENT="production")
    def test_refuses_outside_demo_environment(self):
        with self.assertRaises(CommandError):
            self.run_command("admin@exemplo.local", NEW_PASSWORD)


class ResetDemoAdminWorkflowTests(TestCase):
    def test_workflow_is_manual_and_reads_password_only_from_secret(self):
        workflow = (
            Path(settings.BASE_DIR) / ".github" / "workflows" / "reset-demo-admin-password.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("DEMO_ADMIN_PASSWORD: ${{ secrets.FISCALSEMA_DEMO_ADMIN_PASSWORD }}", workflow)
        self.assertNotIn("inputs.admin_password", workflow)
        self.assertIn("python manage.py reset_demo_admin_password", workflow)
