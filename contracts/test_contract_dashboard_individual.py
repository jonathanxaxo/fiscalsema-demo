from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile

from .services import (
    archive_contract,
    create_contract,
    create_fiscal_substitution,
    share_contract_read_only,
)
from .test_work_orders import WorkOrderBase
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


class IndividualContractDashboardTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order()
        self.client = Client()

    def dashboard_url(self, contract=None):
        return reverse("contracts:dashboard", args=[(contract or self.contract).pk])

    def test_owner_has_stable_dashboard_url_using_existing_calculation_layer(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_contract"], self.contract)
        self.assertEqual(response.context["dashboard"].contract, self.contract)
        self.assertTrue(response.context["contract_dashboard_mode"])
        self.assertContains(response, "Dashboard individual")
        self.assertContains(response, "Contrato 001/2099")
        self.assertContains(response, "Voltar ao painel geral")
        self.assertNotContains(response, 'name="contract"')

    def test_general_dashboard_links_to_individual_contract_dashboard(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"), {"contract": self.contract.pk})
        self.assertContains(response, self.dashboard_url())
        self.assertContains(response, "Dashboard individual")

    def test_other_fiscal_receives_404_and_no_contract_data(self):
        self.client.force_login(self.other)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, self.contract.number, status_code=404)

    def test_consultation_user_sees_only_authorized_dashboard_read_only(self):
        consultation = User.objects.create_user(
            email="consulta.dashboard@example.local",
            full_name="Usuário de Consulta Dashboard",
            password=VALID_PASSWORD,
            profile=UserProfile.CONSULTATION,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=consultation.email,
        )
        self.client.force_login(consultation)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_read_only_access"])
        self.assertFalse(response.context["can_create_item"])
        self.assertContains(response, "Somente leitura")

    def test_fiscal_substitute_sees_dashboard_with_temporary_operational_scope(self):
        today = timezone.localdate()
        create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
            starts_on=today,
            ends_on=today + timedelta(days=5),
        )
        self.client.force_login(self.other)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_substitute_access"])
        self.assertTrue(response.context["can_create_item"])
        self.assertContains(response, "Fiscal substituto")

    def test_administrator_can_consult_but_has_no_operational_write(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_create_item"])
        self.assertFalse(response.context["is_substitute_access"])
        self.assertEqual(response.context["dashboard"].contract, self.contract)

    def test_archived_contract_dashboard_is_not_discoverable(self):
        empty_contract = create_contract(
            actor=self.owner,
            **contract_data(
                number="ARQUIVADO-DASH/2026",
                process_number="PROCESSO-ARQUIVADO-DASH",
            ),
        )
        archive_contract(
            contract_id=empty_contract.pk,
            actor=self.owner,
            reason="Cadastro de teste arquivado.",
            confirmed=True,
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.dashboard_url(empty_contract)).status_code, 404)

    def test_individual_dashboard_never_mixes_another_contract_context(self):
        second = create_contract(
            actor=self.owner,
            **contract_data(
                number="OUTRO-PAINEL/2026",
                process_number="PROCESSO-OUTRO-PAINEL",
            ),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.dashboard_url())
        self.assertEqual(tuple(response.context["contracts"]), (self.contract,))
        self.assertNotContains(response, second.number)
