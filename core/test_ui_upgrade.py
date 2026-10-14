import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from contracts.services import archive_contract, create_contract, share_contract_read_only
from contracts.tests import VALID_PASSWORD, contract_data
from organizations.models import Organization


User = get_user_model()


class InterfaceUpgradeTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="DEMO")
        self.owner = User.objects.create_user(
            email="fiscal.ui@example.local",
            full_name="Fiscal da Interface",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.ui@example.local",
            full_name="Administrador da Interface",
            password=VALID_PASSWORD,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.client = Client()

    def test_contract_list_has_clear_header_status_and_row_actions(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:list"))
        self.assertContains(response, 'class="page-header"')
        self.assertContains(response, "Gestão contratual")
        self.assertContains(response, "status-pill status-success")
        self.assertContains(response, 'class="row-actions"')
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Abrir cadastro")

    def test_contract_detail_groups_actions_without_changing_destinations(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertContains(response, 'class="summary-strip"')
        self.assertContains(response, 'class="action-groups"')
        self.assertContains(response, "Operação")
        self.assertContains(response, "Análise e controle")
        self.assertContains(response, "Gestão do contrato")
        self.assertContains(response, reverse("contracts:dashboard", args=[self.contract.pk]))
        self.assertContains(response, reverse("contracts:archive", args=[self.contract.pk]))

    def test_read_only_detail_does_not_expose_management_actions(self):
        consultation = User.objects.create_user(
            email="consulta.ui@example.local",
            full_name="Consulta da Interface",
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
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertContains(response, "Somente leitura")
        self.assertNotContains(response, "Gestão do contrato")
        self.assertNotContains(response, "Excluir/arquivar cadastro incorreto")

    def test_sensitive_contract_action_is_visually_distinct(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:archive", args=[self.contract.pk]))
        self.assertContains(response, "confirmation-panel confirmation-panel-danger")
        self.assertContains(response, 'class="button-link-danger"')
        self.assertContains(response, "Não haverá exclusão física")

    def test_archived_contract_list_keeps_restore_action_clear(self):
        archive_contract(
            contract_id=self.contract.pk,
            actor=self.owner,
            reason="Cadastro incorreto para teste visual.",
            confirmed=True,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:archived_list"))
        self.assertContains(response, "Histórico preservado")
        self.assertContains(response, "Restaurar")
        self.assertContains(response, "button-link-secondary button-link-small")

    def test_administrative_user_list_has_status_and_grouped_actions(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("accounts_admin:user_list"))
        self.assertContains(response, "Gerencie vínculos e o ciclo de acesso")
        self.assertContains(response, "status-pill status-success")
        self.assertContains(response, 'class="row-actions"')
        self.assertContains(response, "Ver contas excluídas")

    def test_css_has_responsive_and_accessible_components(self):
        stylesheet = Path(finders.find("core/css/app.css")).read_text(encoding="utf-8")
        for selector in (
            ".page-header-actions",
            ".status-pill",
            ".action-groups",
            ".confirmation-panel-danger",
            ".table-responsive:focus",
            ".dashboard-disclosure summary",
            ".explanation-grid",
            "@media (max-width: 600px)",
        ):
            self.assertIn(selector, stylesheet)

    def test_demo_uses_versioned_static_assets_and_vercel_security_headers(self):
        root = Path(__file__).resolve().parent.parent
        demo_settings = (root / "core" / "settings_demo.py").read_text(
            encoding="utf-8"
        )
        vercel_config = json.loads((root / "vercel.json").read_text(encoding="utf-8"))

        self.assertIn("CompressedManifestStaticFilesStorage", demo_settings)
        self.assertIn("FISCALSEMA_DEMO_DATABASE_URL", demo_settings)
        self.assertIn(
            'os.environ["DATABASE_URL"] = dedicated_database_url', demo_settings
        )
        self.assertNotIn("rewrites", vercel_config)
        security_headers = {
            item["key"]: item["value"]
            for rule in vercel_config["headers"]
            for item in rule["headers"]
        }
        self.assertEqual(security_headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(security_headers["X-Frame-Options"], "DENY")
        self.assertEqual(security_headers["Referrer-Policy"], "same-origin")
        self.assertEqual(
            security_headers["Permissions-Policy"],
            "camera=(), microphone=(), geolocation=()",
        )

    def test_javascript_improves_live_messages_and_table_names(self):
        script = Path(finders.find("core/js/app.js")).read_text(encoding="utf-8")
        self.assertIn("aria-live", script)
        self.assertIn("sectionTitle", script)
        self.assertIn("Tabela:", script)
