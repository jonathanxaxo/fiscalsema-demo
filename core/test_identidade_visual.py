from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountStatus
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization


class IdentidadeVisualTests(TestCase):
    def test_logo_and_favicon_are_versioned_static_files(self):
        self.assertIsNotNone(finders.find("core/img/logo.svg"))
        self.assertIsNotNone(finders.find("core/img/favicon.svg"))

    def test_login_shows_logo_favicon_and_new_name(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertContains(response, "core/img/favicon.svg")
        self.assertContains(response, "core/img/logo.svg")
        self.assertContains(response, "<title>Entrar — FiscalSema</title>", html=False)
        self.assertNotContains(response, "FiscalSema Light")

    def test_authenticated_menu_uses_svg_icons(self):
        user = get_user_model().objects.create_user(
            email="identidade@example.local",
            full_name="Fiscal Identidade",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=Organization.objects.create(name="DEMO"),
        )
        self.client.force_login(user)
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="nav-icon"')
        self.assertContains(response, "Fiscalização de contratos")
        self.assertNotContains(response, '<span aria-hidden="true">⌂</span>', html=False)
