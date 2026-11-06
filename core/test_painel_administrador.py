from django.test import TestCase
from django.urls import reverse

from accounts.models import AccountStatus, AuthenticationEvent, RegistrationRequest, User
from contracts.services import create_contract
from contracts.tests import VALID_PASSWORD, contract_data
from organizations.models import Organization


class PainelAdministradorTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="SEMA")
        self.admin = User.objects.create_superuser(
            email="admin.painel@example.local", full_name="Administrador Painel", password=VALID_PASSWORD
        )
        self.fiscal = User.objects.create_user(
            email="fiscal.painel@example.local",
            full_name="Fiscal Painel",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.contract = create_contract(actor=self.fiscal, **contract_data())
        pending = User.objects.create_user(
            email="pendente.painel@example.local",
            full_name="Pessoa Pendente",
            password=VALID_PASSWORD,
        )
        self.registration = RegistrationRequest.objects.create(user=pending)
        AuthenticationEvent.objects.create(event_type=AuthenticationEvent.EventType.LOGIN_FAILURE)

    def test_administrator_home_shows_access_control_only(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "core/admin_home.html")
        self.assertContains(response, "Controle de acessos")
        self.assertContains(response, "Solicitações de cadastro")
        self.assertContains(response, "Pessoa Pendente")
        self.assertContains(response, reverse("accounts_admin:registration_review", args=[self.registration.pk]))
        self.assertContains(response, "Contas ativas por perfil")
        self.assertContains(response, "Falhas de login (24 h)")
        self.assertNotContains(response, "Painel do contrato")
        self.assertNotContains(response, self.contract.number)
        dashboard = response.context["admin_dashboard"]
        self.assertEqual(dashboard["pending_count"], 1)
        self.assertEqual(dashboard["login_failures_24h"], 1)
        self.assertEqual(dashboard["users_total"], 3)
        self.assertEqual(response.context["pending_registration_count"], 1)

    def test_contract_parameter_does_not_bring_contracts_to_admin_home(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"), {"contract": self.contract.pk})
        self.assertTemplateUsed(response, "core/admin_home.html")
        self.assertNotContains(response, "Painel do contrato")

    def test_fiscal_home_is_unchanged(self):
        self.client.force_login(self.fiscal)
        response = self.client.get(reverse("home"))
        self.assertTemplateUsed(response, "home.html")
        self.assertContains(response, "Painel do contrato")
        self.assertContains(response, self.contract.number)
        self.assertNotContains(response, "Controle de acessos")
