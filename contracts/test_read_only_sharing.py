from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, RegistrationRequest, UserProfile
from accounts.services import review_registration_request

from .models import (
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractInvitation,
    ContractInvitationStatus,
    ContractSharingEvent,
    WorkOrderStatus,
)
from .services import (
    contracts_visible_to,
    contracts_writable_by,
    items_visible_to,
    revoke_contract_access,
    share_contract_read_only,
    update_contract,
)
from .test_work_orders import WorkOrderBase
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


class ReadOnlySharingTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("10.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.client = Client()

    def share_with_other(self):
        access, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
        )
        self.assertIsNone(invitation)
        return access

    def test_existing_account_receives_only_read_access_with_audit(self):
        access = self.share_with_other()
        self.assertEqual(access.access_type, ContractAccessType.READ_ONLY)
        self.assertEqual(access.status, ContractAccessStatus.ACTIVE)
        self.assertEqual(access.granted_by, self.owner)
        self.assertIn(self.contract, contracts_visible_to(self.other))
        self.assertFalse(contracts_writable_by(self.other).filter(pk=self.contract.pk).exists())
        event = ContractSharingEvent.objects.get(
            event_type=ContractSharingEvent.EventType.ACCESS_GRANTED
        )
        self.assertEqual(event.access, access)
        self.assertEqual(event.actor, self.owner)

    def test_unknown_email_creates_pending_invitation_without_invented_expiry(self):
        access, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="  CONVIDADO@EXAMPLE.LOCAL ",
        )
        self.assertIsNone(access)
        self.assertEqual(invitation.email, "convidado@example.local")
        self.assertEqual(invitation.status, ContractInvitationStatus.PENDING)
        self.assertIsNone(invitation.expires_at)
        self.assertTrue(
            ContractSharingEvent.objects.filter(
                invitation=invitation,
                event_type=ContractSharingEvent.EventType.INVITATION_CREATED,
            ).exists()
        )

    def test_invitation_waits_for_account_approval_before_granting_access(self):
        _, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="novo.leitor@example.local",
        )
        reader = User.objects.create_user(
            email="NOVO.LEITOR@example.local",
            full_name="Novo Leitor",
            password=VALID_PASSWORD,
            status=AccountStatus.PENDING_APPROVAL,
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ContractInvitationStatus.PENDING)
        self.assertIsNone(invitation.accepted_by)
        self.assertFalse(
            ContractAccess.objects.filter(contract=self.contract, user=reader).exists()
        )
        self.assertEqual(User.objects.filter(email__iexact=reader.email).count(), 1)
        self.assertFalse(contracts_visible_to(reader).exists())
        reader.status = AccountStatus.ACTIVE
        reader.organization = self.organization
        reader.save(update_fields=("status", "organization"))
        invitation.refresh_from_db()
        access = ContractAccess.objects.get(contract=self.contract, user=reader)
        self.assertEqual(invitation.status, ContractInvitationStatus.ACCEPTED)
        self.assertEqual(invitation.accepted_by, reader)
        self.assertIn(self.contract, contracts_visible_to(reader))
        self.assertEqual(access.access_type, ContractAccessType.READ_ONLY)

    def test_invited_public_registration_becomes_consultation_after_approval(self):
        _, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="consulta.cadastrada@example.local",
        )
        response = self.client.post(
            reverse("accounts:register"),
            {
                "full_name": "Pessoa Convidada",
                "email": "CONSULTA.CADASTRADA@example.local",
                "organization_name": "Organização informada",
                "sector_name": "Setor informado",
                "phone": "",
                "password1": VALID_PASSWORD,
                "password2": VALID_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        reader = User.objects.get(email="consulta.cadastrada@example.local")
        self.assertEqual(reader.profile, UserProfile.CONSULTATION)
        self.assertEqual(reader.status, AccountStatus.PENDING_APPROVAL)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ContractInvitationStatus.PENDING)
        self.assertFalse(
            ContractAccess.objects.filter(contract=self.contract, user=reader).exists()
        )

        review_registration_request(
            request_id=RegistrationRequest.objects.get(user=reader).pk,
            actor=self.admin,
            action="approve",
            organization_id=self.organization.pk,
        )
        reader.refresh_from_db()
        invitation.refresh_from_db()
        self.assertEqual(reader.status, AccountStatus.ACTIVE)
        self.assertEqual(reader.profile, UserProfile.CONSULTATION)
        self.assertEqual(invitation.status, ContractInvitationStatus.ACCEPTED)
        self.assertIn(self.contract, contracts_visible_to(reader))

    def test_pending_existing_account_receives_invitation_not_early_access(self):
        pending = User.objects.create_user(
            email="conta.pendente@example.local",
            full_name="Conta Pendente",
            password=VALID_PASSWORD,
            status=AccountStatus.PENDING_APPROVAL,
        )
        access, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=pending.email,
        )
        self.assertIsNone(access)
        self.assertEqual(invitation.status, ContractInvitationStatus.PENDING)
        self.assertFalse(
            ContractAccess.objects.filter(contract=self.contract, user=pending).exists()
        )

    def test_ineligible_existing_accounts_must_be_regularized(self):
        accounts = (
            ("inativa@example.local", AccountStatus.INACTIVE, {}),
            ("bloqueada@example.local", AccountStatus.BLOCKED, {}),
            ("rejeitada@example.local", AccountStatus.REJECTED, {}),
            (
                "arquivada@example.local",
                AccountStatus.INACTIVE,
                {"archived_at": timezone.now(), "archived_by": self.admin},
            ),
        )
        for email, status, extra in accounts:
            with self.subTest(status=status, archived=bool(extra)):
                user = User.objects.create_user(
                    email=email,
                    full_name="Conta sem elegibilidade",
                    password=VALID_PASSWORD,
                    status=status,
                    **extra,
                )
                with self.assertRaisesMessage(ValidationError, "regularizada"):
                    share_contract_read_only(
                        contract_id=self.contract.pk,
                        actor=self.owner,
                        email=user.email,
                    )

    def test_revoked_access_requires_explicit_regrant_confirmation(self):
        access = self.share_with_other()
        revoke_contract_access(
            access_id=access.pk,
            contract_id=self.contract.pk,
            actor=self.owner,
        )
        with self.assertRaisesMessage(ValidationError, "confirmação"):
            share_contract_read_only(
                contract_id=self.contract.pk,
                actor=self.owner,
                email=self.other.email,
            )
        reactivated, _ = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
            confirm_regrant=True,
        )
        self.assertEqual(reactivated.pk, access.pk)
        self.assertEqual(reactivated.status, ContractAccessStatus.ACTIVE)
        self.assertIsNone(reactivated.revoked_at)
        self.assertTrue(
            ContractSharingEvent.objects.filter(
                access=reactivated,
                event_type=ContractSharingEvent.EventType.ACCESS_GRANTED,
                details__reativacao=True,
            ).exists()
        )

    def test_shared_user_sees_contract_children_dashboard_accountability_and_report(self):
        self.share_with_other()
        self.assertIn(self.item, items_visible_to(self.other))
        self.client.force_login(self.other)
        for url in (
            reverse("home") + f"?contract={self.contract.pk}",
            reverse("contracts:detail", args=[self.contract.pk]),
            reverse("contracts:item_list", args=[self.contract.pk]),
            reverse("contracts:work_order_list", args=[self.contract.pk]),
            reverse("contracts:accountability", args=[self.contract.pk]),
            reverse("contracts:report", args=[self.contract.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Somente leitura")

    def test_shared_user_cannot_call_write_services_or_direct_write_urls(self):
        self.share_with_other()
        with self.assertRaises(type(self.contract).DoesNotExist):
            update_contract(
                contract_id=self.contract.pk,
                actor=self.other,
                **contract_data(object="Tentativa indevida"),
            )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:item_create", args=[self.contract.pk])
            ).status_code,
            403,
        )
        detail = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertNotContains(detail, reverse("contracts:update", args=[self.contract.pk]))

    def test_consultation_profile_reads_only_explicitly_shared_contract(self):
        consultation = User.objects.create_user(
            email="consulta.contrato@example.local",
            full_name="Usuário de Consulta",
            password=VALID_PASSWORD,
            profile=UserProfile.CONSULTATION,
            status=AccountStatus.ACTIVE,
        )
        self.assertFalse(contracts_visible_to(consultation).exists())
        share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=consultation.email,
        )
        self.assertIn(self.contract, contracts_visible_to(consultation))
        self.assertFalse(
            contracts_writable_by(consultation).filter(pk=self.contract.pk).exists()
        )
        self.assertTrue(consultation.has_perm("contracts.view_contract"))
        self.assertTrue(consultation.has_perm("contracts.view_payment"))
        self.assertTrue(consultation.has_perm("documents.view_document"))
        self.assertFalse(consultation.has_perm("contracts.add_contract"))
        self.assertFalse(consultation.has_perm("contracts.change_contract"))
        self.assertFalse(consultation.has_perm("contracts.add_payment"))
        self.assertFalse(consultation.has_perm("documents.add_document"))

        self.client.force_login(consultation)
        dashboard = self.client.get(reverse("home") + f"?contract={self.contract.pk}")
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, "Somente leitura")
        self.assertEqual(self.client.get(reverse("contracts:create")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )

    def test_read_only_user_cannot_view_or_change_access_management(self):
        self.share_with_other()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(
                reverse("contracts:access_list", args=[self.contract.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:access_share", args=[self.contract.pk])
            ).status_code,
            403,
        )

    def test_owner_shares_through_web_and_sees_access_list(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:access_share", args=[self.contract.pk]),
            {"email": self.other.email},
        )
        self.assertRedirects(
            response, reverse("contracts:access_list", args=[self.contract.pk])
        )
        listing = self.client.get(
            reverse("contracts:access_list", args=[self.contract.pk])
        )
        self.assertContains(listing, self.other.email)
        self.assertContains(listing, "Somente leitura")
        self.assertContains(listing, "Revogações e cancelamentos preservam")

    def test_administrator_can_audit_list_but_cannot_share(self):
        self.share_with_other()
        self.client.force_login(self.admin)
        listing = self.client.get(
            reverse("contracts:access_list", args=[self.contract.pk])
        )
        self.assertEqual(listing.status_code, 200)
        self.assertNotContains(
            listing, reverse("contracts:access_share", args=[self.contract.pk])
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:access_share", args=[self.contract.pk])
            ).status_code,
            403,
        )

    def test_duplicate_owner_and_cross_contract_sharing_are_rejected(self):
        self.share_with_other()
        with self.assertRaisesMessage(ValidationError, "já possui"):
            share_contract_read_only(
                contract_id=self.contract.pk,
                actor=self.owner,
                email=self.other.email,
            )
        with self.assertRaisesMessage(ValidationError, "responsável"):
            share_contract_read_only(
                contract_id=self.contract.pk,
                actor=self.owner,
                email=self.owner.email,
            )
        with self.assertRaises(type(self.contract).DoesNotExist):
            share_contract_read_only(
                contract_id=self.contract.pk,
                actor=self.other,
                email="terceiro@example.local",
            )

    def test_duplicate_pending_invitation_is_rejected(self):
        share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="pendente@example.local",
        )
        with self.assertRaisesMessage(ValidationError, "convite pendente"):
            share_contract_read_only(
                contract_id=self.contract.pk,
                actor=self.owner,
                email="PENDENTE@example.local",
            )

    def test_access_and_invitation_cannot_be_deleted(self):
        access = self.share_with_other()
        _, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email="preservar@example.local",
        )
        with self.assertRaisesMessage(ValidationError, "não pode ser excluído"):
            access.delete()
        with self.assertRaisesMessage(ValidationError, "não pode ser excluído"):
            invitation.delete()

    def test_only_read_only_type_exists(self):
        self.assertEqual(ContractAccessType.values, ["READ_ONLY"])
