"""Página Metodologia e visual compacto (Sprint 20)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountStatus
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

User = get_user_model()


class MetodologiaTests(TestCase):
    def setUp(self):
        organization = Organization.objects.create(name="Organização Metodologia")
        self.fiscal = User.objects.create_user(
            email="fiscal.metodo@example.local",
            full_name="Fiscal Metodologia",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.metodo@example.local",
            full_name="Administrador Metodologia",
            password=VALID_PASSWORD,
        )
        self.url = reverse("methodology")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_page_shows_the_four_requested_sections(self):
        self.client.force_login(self.fiscal)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/metodologia.html")
        for section in ('id="metodo"', 'id="sprints"', 'id="tecnologias"', 'id="ia"', 'id="seguranca"'):
            self.assertContains(response, section)
        for text in ("Entender", "Registrar", "Django 5.2", "PostgreSQL", "Claude Code e Codex",
                     "Matriz de autonomia", "a decisão e a validação continuam humanas"):
            self.assertContains(response, text)

    def test_menu_link_for_fiscal_and_administrator(self):
        for user in (self.fiscal, self.admin):
            with self.subTest(user=user.email):
                self.client.force_login(user)
                response = self.client.get(reverse("home"))
                self.assertContains(response, f'href="{self.url}"')
                self.assertContains(response, "Metodologia</a>")

    def test_only_get_is_allowed(self):
        self.client.force_login(self.fiscal)
        self.assertEqual(self.client.post(self.url).status_code, 405)

    def test_latest_sprint_is_listed_in_methodology(self):
        import re
        from pathlib import Path

        from django.conf import settings

        sprints = Path(settings.BASE_DIR, "docs", "sprints")
        numbers = [int(m.group(1)) for d in sprints.iterdir() if (m := re.match(r"sprint-(\d+)-", d.name))]
        self.client.force_login(self.fiscal)
        response = self.client.get(self.url)
        self.assertContains(response, f"<b>{max(numbers):02d}</b>")

