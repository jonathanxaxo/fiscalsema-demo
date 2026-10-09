from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, RegistrationRequest, UserProfile
from accounts.services import review_registration_request
from organizations.models import Organization

from .models import (
    FiscalSubstitution,
    FiscalSubstitutionEvent,
    FiscalSubstitutionStatus,
)
from .services import (
    contracts_visible_to,
    contracts_writable_by,
    create_contract,
    create_fiscal_substitution,
    revoke_fiscal_substitution,
)
from .test_work_orders import WorkOrderBase
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


class FiscalSubstitutionTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.today = timezone.localdate()

    def create_current_substitution(self, user=None):
        user = user or self.other
        return create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=user.email,
            starts_on=self.today,
            ends_on=self.today + timedelta(days=7),
        )

    def test_active_fiscal_receives_temporary_operational_access(self):
        substitution = self.create_current_substitution()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.LINKED)
        self.assertTrue(substitution.is_effective)
        self.assertIn(self.contract, contracts_visible_to(self.other))
        self.assertIn(self.contract, contracts_writable_by(self.other))

        self.client.force_login(self.other)
        listing = self.client.get(reverse("contracts:list"))
        self.assertContains(listing, "Fiscal substituto")
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            200,
        )

    def test_substitute_keeps_own_contract_and_receives_second_contract(self):
        own_contract = create_contract(
            actor=self.other,
            **contract_data(number="SUB-001/2026", process_number="SUB-PROCESSO-1"),
        )
        self.create_current_substitution()
        visible_ids = set(contracts_visible_to(self.other).values_list("pk", flat=True))
        writable_ids = set(contracts_writable_by(self.other).values_list("pk", flat=True))
        self.assertEqual(visible_ids, {self.contract.pk, own_contract.pk})
        self.assertEqual(writable_ids, {self.contract.pk, own_contract.pk})

    def test_future_period_does_not_grant_early_access(self):
        substitution = create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
            starts_on=self.today + timedelta(days=10),
            ends_on=self.today + timedelta(days=20),
        )
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.LINKED)
        self.assertFalse(substitution.is_effective)
        self.assertNotIn(self.contract, contracts_visible_to(self.other))
        self.assertNotIn(self.contract, contracts_writable_by(self.other))

    def test_unknown_email_registers_as_fiscal_and_links_only_after_approval(self):
        substitution = create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="substituto.novo@example.local",
            starts_on=self.today,
            ends_on=self.today + timedelta(days=5),
        )
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.PENDING_ACCOUNT)
        response = self.client.post(
            reverse("accounts:register"),
            {
                "full_name": "Fiscal Substituto Novo",
                "email": "SUBSTITUTO.NOVO@example.local",
                "organization_name": self.organization.name,
                "sector_name": "",
                "phone": "",
                "password1": VALID_PASSWORD,
                "password2": VALID_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        substitute = User.objects.get(email="substituto.novo@example.local")
        self.assertEqual(substitute.profile, UserProfile.FISCAL)
        substitution.refresh_from_db()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.PENDING_ACCOUNT)
        self.assertNotIn(self.contract, contracts_visible_to(substitute))

        review_registration_request(
            request_id=RegistrationRequest.objects.get(user=substitute).pk,
            actor=self.admin,
            action="approve",
            organization_id=self.organization.pk,
        )
        substitute.refresh_from_db()
        substitution.refresh_from_db()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.LINKED)
        self.assertEqual(substitution.substitute, substitute)
        self.assertIn(self.contract, contracts_writable_by(substitute))

    def test_read_only_invite_and_substitution_prioritize_fiscal_profile(self):
        from .services import share_contract_read_only

        email = "duplo.convite@example.local"
        share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=email,
        )
        create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=email,
            starts_on=self.today,
            ends_on=self.today + timedelta(days=5),
        )
        self.client.post(
            reverse("accounts:register"),
            {
                "full_name": "Fiscal com dois convites",
                "email": email,
                "organization_name": self.organization.name,
                "sector_name": "",
                "phone": "",
                "password1": VALID_PASSWORD,
                "password2": VALID_PASSWORD,
            },
        )
        self.assertEqual(User.objects.get(email=email).profile, UserProfile.FISCAL)

    def test_ineligible_profile_status_and_other_organization_are_rejected(self):
        consultation = User.objects.create_user(
            email="consulta.substituta@example.local",
            full_name="Consulta",
            password=VALID_PASSWORD,
            profile=UserProfile.CONSULTATION,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        with self.assertRaisesMessage(ValidationError, "perfil Fiscal"):
            self.create_current_substitution(consultation)

        inactive = User.objects.create_user(
            email="inativa.substituta@example.local",
            full_name="Inativa",
            password=VALID_PASSWORD,
            status=AccountStatus.INACTIVE,
            organization=self.organization,
        )
        with self.assertRaisesMessage(ValidationError, "regularizada"):
            self.create_current_substitution(inactive)

        other_organization = Organization.objects.create(name="Outra organização")
        foreign_fiscal = User.objects.create_user(
            email="outra.organizacao@example.local",
            full_name="Fiscal de outra organização",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=other_organization,
        )
        with self.assertRaisesMessage(ValidationError, "organização do contrato"):
            self.create_current_substitution(foreign_fiscal)

    def test_period_must_be_valid_inside_contract_and_without_overlap(self):
        self.create_current_substitution()
        with self.assertRaisesMessage(ValidationError, "nesse período"):
            create_fiscal_substitution(
                contract_id=self.contract.pk,
                actor=self.owner,
                email="sobreposto@example.local",
                starts_on=self.today + timedelta(days=1),
                ends_on=self.today + timedelta(days=2),
            )
        with self.assertRaisesMessage(ValidationError, "vigência do contrato"):
            create_fiscal_substitution(
                contract_id=self.contract.pk,
                actor=self.owner,
                email="fora.vigencia@example.local",
                starts_on=self.contract.validity_end,
                ends_on=self.contract.validity_end + timedelta(days=1),
            )

    def test_revocation_removes_access_immediately_and_preserves_audit(self):
        substitution = self.create_current_substitution()
        revoke_fiscal_substitution(
            substitution_id=substitution.pk,
            contract_id=self.contract.pk,
            actor=self.owner,
        )
        substitution.refresh_from_db()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.REVOKED)
        self.assertNotIn(self.contract, contracts_writable_by(self.other))
        self.assertTrue(
            FiscalSubstitutionEvent.objects.filter(
                substitution=substitution,
                event_type=FiscalSubstitutionEvent.EventType.REVOKED,
                actor=self.owner,
            ).exists()
        )
        with self.assertRaisesMessage(ValidationError, "não pode ser excluída"):
            substitution.delete()

    def test_substitution_audit_event_is_immutable_in_postgresql(self):
        substitution = self.create_current_substitution()
        event = FiscalSubstitutionEvent.objects.filter(
            substitution=substitution,
            event_type=FiscalSubstitutionEvent.EventType.CREATED,
        ).get()
        with self.assertRaises(DatabaseError), transaction.atomic():
            FiscalSubstitutionEvent.objects.filter(pk=event.pk).update(
                details={"violado": True}
            )
        with self.assertRaises(DatabaseError), transaction.atomic():
            FiscalSubstitutionEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(FiscalSubstitutionEvent.objects.filter(pk=event.pk).exists())

    def test_substitute_cannot_delegate_or_manage_substitutions(self):
        self.create_current_substitution()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(
                reverse("contracts:access_list", args=[self.contract.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:substitution_create", args=[self.contract.pk])
            ).status_code,
            403,
        )

    def test_web_flow_lists_and_revokes_substitution(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:substitution_create", args=[self.contract.pk]),
            {
                "email": self.other.email,
                "starts_on": self.today.isoformat(),
                "ends_on": (self.today + timedelta(days=3)).isoformat(),
            },
        )
        self.assertRedirects(
            response, reverse("contracts:access_list", args=[self.contract.pk])
        )
        substitution = FiscalSubstitution.objects.get(contract=self.contract)
        listing = self.client.get(reverse("contracts:access_list", args=[self.contract.pk]))
        self.assertContains(listing, self.other.email)
        revoke_url = reverse(
            "contracts:substitution_revoke",
            args=[self.contract.pk, substitution.pk],
        )
        self.assertContains(listing, revoke_url)
        self.assertRedirects(
            self.client.post(revoke_url),
            reverse("contracts:access_list", args=[self.contract.pk]),
        )
        substitution.refresh_from_db()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.REVOKED)
