from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile

from .models import Organization, OrganizationEvent, Sector
from .services import create_organization, update_sector


User = get_user_model()
VALID_PASSWORD = "SenhaMuitoForte!2026"


class OrganizationModelTests(TestCase):
    def test_organization_name_is_normalized_and_unique_ignoring_case(self):
        organization = Organization.objects.create(name="  Secretaria   Estadual  ")
        self.assertEqual(organization.name, "Secretaria Estadual")
        with self.assertRaises(ValidationError):
            Organization.objects.create(name="secretaria estadual")

    def test_sector_is_unique_inside_organization_but_reusable_elsewhere(self):
        first = Organization.objects.create(name="Primeira")
        second = Organization.objects.create(name="Segunda")
        Sector.objects.create(organization=first, name="Financeiro")
        Sector.objects.create(organization=second, name="Financeiro")
        with self.assertRaises(ValidationError):
            Sector.objects.create(organization=first, name="financeiro")

    def test_active_sector_requires_active_organization(self):
        organization = Organization.objects.create(name="Inativa", is_active=False)
        with self.assertRaisesMessage(
            ValidationError, "Um setor ativo exige organização ativa."
        ):
            Sector.objects.create(organization=organization, name="Setor")
        sector = Sector.objects.create(
            organization=organization, name="Setor inativo", is_active=False
        )
        self.assertFalse(sector.is_active)

    def test_user_sector_must_belong_to_user_organization(self):
        first = Organization.objects.create(name="Primeira")
        second = Organization.objects.create(name="Segunda")
        sector = Sector.objects.create(organization=second, name="Setor")
        with self.assertRaisesMessage(
            ValidationError, "O setor deve pertencer à organização selecionada."
        ):
            User.objects.create_user(
                email="invalido@example.local",
                full_name="Vínculo Inválido",
                password=VALID_PASSWORD,
                organization=first,
                sector=sector,
            )


class OrganizationAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.organizacoes@example.local",
            full_name="Administrador Organizações",
            password=VALID_PASSWORD,
        )
        self.fiscal = User.objects.create_user(
            email="fiscal.organizacoes@example.local",
            full_name="Fiscal Organizações",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )
        self.client = Client()

    def test_administrator_group_receives_management_permission(self):
        administrator = User.objects.create_user(
            email="gestor.organizacoes@example.local",
            full_name="Gestor Organizações",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.assertTrue(administrator.has_perm("organizations.manage_organizations"))

    def test_administrator_creates_organization_and_sector_with_audit(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("organizations:organization_create"),
            {"name": "DEMO", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("organizations:organization_list"))
        organization = Organization.objects.get(name="DEMO")
        self.assertEqual(organization.created_by, self.admin)
        self.assertTrue(OrganizationEvent.objects.filter(
            event_type=OrganizationEvent.EventType.ORGANIZATION_CREATED,
            organization=organization,
            actor=self.admin,
        ).exists())
        response = self.client.post(
            reverse("organizations:sector_create"),
            {"organization": organization.pk, "name": "GSAAS", "is_active": "on"},
        )
        self.assertRedirects(response, reverse("organizations:sector_list"))
        sector = Sector.objects.get(name="GSAAS")
        self.assertTrue(OrganizationEvent.objects.filter(
            event_type=OrganizationEvent.EventType.SECTOR_CREATED,
            sector=sector,
            actor=self.admin,
        ).exists())

    def test_administrator_assigns_existing_user_with_audit(self):
        organization = Organization.objects.create(name="Organização")
        sector = Sector.objects.create(organization=organization, name="Setor")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts_admin:user_organization", args=[self.fiscal.pk]),
            {"organization": organization.pk, "sector": sector.pk},
        )
        self.assertRedirects(response, reverse("accounts_admin:user_list"))
        self.fiscal.refresh_from_db()
        self.assertEqual(self.fiscal.organization, organization)
        self.assertEqual(self.fiscal.sector, sector)
        event = OrganizationEvent.objects.get(
            event_type=OrganizationEvent.EventType.USER_ASSIGNED,
            user=self.fiscal,
        )
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.details["origem"], "correcao_administrativa")
        self.assertEqual(event.details["anterior"], {"organizacao_id": None, "setor_id": None})

    def test_deactivating_organization_deactivates_sectors_and_is_audited(self):
        organization = Organization.objects.create(name="Organização")
        sector = Sector.objects.create(organization=organization, name="Setor")
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("organizations:organization_update", args=[organization.pk]),
            {"name": organization.name},
        )
        self.assertRedirects(response, reverse("organizations:organization_list"))
        organization.refresh_from_db()
        sector.refresh_from_db()
        self.assertFalse(organization.is_active)
        self.assertFalse(sector.is_active)
        event = OrganizationEvent.objects.get(
            event_type=OrganizationEvent.EventType.ORGANIZATION_DEACTIVATED,
            organization=organization,
        )
        self.assertEqual(event.details["setores_inativados"], 1)
        self.assertEqual(event.details["setores_inativados_ids"], [sector.pk])
        self.assertTrue(OrganizationEvent.objects.filter(
            event_type=OrganizationEvent.EventType.SECTOR_DEACTIVATED,
            sector=sector,
            details__origem="inativacao_organizacao",
        ).exists())

    def test_status_actions_hide_and_restore_organization_and_sector(self):
        organization = Organization.objects.create(name="Organização Operacional")
        sector = Sector.objects.create(organization=organization, name="Setor Operacional")
        self.client.force_login(self.admin)
        self.assertContains(
            self.client.get(reverse("organizations:organization_list")), organization.name
        )

        self.client.post(reverse("organizations:organization_status", args=[organization.pk]))
        organization.refresh_from_db()
        sector.refresh_from_db()
        self.assertFalse(organization.is_active)
        self.assertFalse(sector.is_active)
        self.assertNotContains(
            self.client.get(reverse("organizations:organization_list")), organization.name
        )
        self.assertContains(
            self.client.get(reverse("organizations:organization_list") + "?inativos=1"),
            organization.name,
        )

        self.client.post(reverse("organizations:organization_status", args=[organization.pk]))
        organization.refresh_from_db()
        self.assertTrue(organization.is_active)
        sector.refresh_from_db()
        self.assertFalse(sector.is_active)
        self.client.post(reverse("organizations:sector_status", args=[sector.pk]))
        sector.refresh_from_db()
        self.assertTrue(sector.is_active)
        self.assertContains(self.client.get(reverse("organizations:sector_list")), sector.name)

    def test_sector_with_users_cannot_move_to_another_organization(self):
        first = Organization.objects.create(name="Primeira")
        second = Organization.objects.create(name="Segunda")
        sector = Sector.objects.create(organization=first, name="Setor")
        self.fiscal.organization = first
        self.fiscal.sector = sector
        self.fiscal.save()
        with self.assertRaisesMessage(
            ValidationError, "Não é possível transferir um setor que possui usuários vinculados."
        ):
            update_sector(
                sector_id=sector.pk,
                actor=self.admin,
                organization=second,
                name=sector.name,
                is_active=True,
            )

    def test_fiscal_cannot_manage_or_see_organization_menu(self):
        self.client.force_login(self.fiscal)
        self.assertNotContains(
            self.client.get(reverse("home")), reverse("organizations:organization_list")
        )
        for url in (
            reverse("organizations:organization_list"),
            reverse("organizations:organization_create"),
            reverse("organizations:sector_list"),
            reverse("organizations:sector_create"),
            reverse("accounts_admin:user_list"),
            reverse("accounts_admin:user_organization", args=[self.fiscal.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        with self.assertRaises(PermissionDenied):
            create_organization(actor=self.fiscal, name="Negada")

    def test_administrator_sees_organization_and_user_links(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("organizations:organization_list"))
        self.assertContains(response, reverse("organizations:sector_list"))
        self.assertContains(response, reverse("accounts_admin:user_list"))

    def test_django_admin_is_read_only_for_organizations(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:organizations_organization_add")).status_code,
            403,
        )
