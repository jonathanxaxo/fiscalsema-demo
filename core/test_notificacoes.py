"""Sino de notificações no topo (Sprint 14, adaptado do sistema principal)."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, RegistrationRequest
from contracts.models import ContractStatus
from contracts.services import create_contract, share_contract_read_only
from contracts.tests import VALID_PASSWORD, contract_data
from core.notifications import build_notifications
from organizations.models import Organization

User = get_user_model()


class TopbarNotificationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SEMA")
        self.fiscal = User.objects.create_user(
            email="fiscal.sino@example.local",
            full_name="Fiscal do Sino",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.reader = User.objects.create_user(
            email="leitor.sino@example.local",
            full_name="Leitor do Sino",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.sino@example.local",
            full_name="Administrador do Sino",
            password=VALID_PASSWORD,
        )
        self.contract = create_contract(actor=self.fiscal, **contract_data())
        self.client = Client()

    def test_fiscal_notification_points_to_exact_place_to_fix(self):
        # Contrato sem itens: a soma dos itens diverge do valor atual.
        notes = build_notifications(self.fiscal)
        note = next(n for n in notes["items"] if "A soma dos itens" in n["title"])
        self.assertIn("diverge do valor atual do contrato", note["title"])
        self.assertEqual(note["url"], reverse("contracts:item_list", args=[self.contract.pk]))
        self.assertEqual(note["hint"], "Abrir itens para conferir")
        self.assertEqual(notes["count"], len(notes["items"]) + notes["hidden_count"])

    def test_bell_is_rendered_with_count_for_fiscal(self):
        self.client.force_login(self.fiscal)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "data-notifications")
        self.assertContains(response, 'class="notifications-count"')
        self.assertContains(response, "diverge do valor atual do contrato")
        self.assertContains(response, "Abrir itens para conferir")

    def test_admin_bell_only_shows_registrations(self):
        notes = build_notifications(self.admin)
        self.assertEqual(notes["count"], 0)
        pending = User.objects.create_user(
            email="pendente.sino@example.local", full_name="Pendente", password=VALID_PASSWORD
        )
        RegistrationRequest.objects.create(user=pending)
        notes = build_notifications(self.admin)
        self.assertEqual(notes["count"], 1)
        self.assertEqual(notes["items"][0]["url"], reverse("accounts_admin:registration_list"))
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"))
        self.assertNotContains(response, f"<small>Contrato {self.contract.number} ·")

    def test_closed_contracts_do_not_notify(self):
        type(self.contract).objects.filter(pk=self.contract.pk).update(status=ContractStatus.CLOSED)
        self.assertEqual(build_notifications(self.fiscal)["count"], 0)

    def test_read_only_user_is_sent_to_contract_panel(self):
        share_contract_read_only(contract_id=self.contract.pk, actor=self.fiscal, email=self.reader.email)
        notes = build_notifications(self.reader)
        self.assertGreaterEqual(notes["count"], 1)
        panel = reverse("contracts:dashboard", args=[self.contract.pk])
        self.assertTrue(all(note["url"] == panel for note in notes["items"]))
        self.assertTrue(all(note["hint"] == "Ver no painel do contrato" for note in notes["items"]))

    def test_contract_pages_only_list_that_contract(self):
        other = create_contract(actor=self.fiscal, **contract_data(number="OUTRO/2099", process_number="P-2"))
        self.client.force_login(self.fiscal)
        general = self.client.get(reverse("home"))
        self.assertContains(general, f"<small>Contrato {self.contract.number} ·")
        self.assertContains(general, f"<small>Contrato {other.number} ·")
        scoped = self.client.get(reverse("contracts:item_list", args=[self.contract.pk]))
        self.assertContains(scoped, f"<small>Contrato {self.contract.number} ·")
        self.assertNotContains(scoped, f"<small>Contrato {other.number} ·")

    def test_notification_text_can_wrap_inside_user_menu(self):
        from django.contrib.staticfiles import finders

        with open(finders.find("core/css/app.css"), encoding="utf-8") as stylesheet:
            css = stylesheet.read()
        self.assertIn(".user-menu > a { font-weight: 650; white-space: nowrap; }", css)
        self.assertNotIn(".user-menu a { font-weight: 650; white-space: nowrap; }", css)
        self.assertIn(".notification { white-space: normal;", css)
