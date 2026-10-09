from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from accounts.models import AccountStatus

from .models import (
    ContractAccess,
    ContractAccessStatus,
    ContractInvitationStatus,
    ContractSharingEvent,
)
from .services import (
    cancel_contract_invitation,
    contracts_visible_to,
    revoke_contract_access,
    share_contract_read_only,
)
from .test_work_orders import WorkOrderBase
from .tests import VALID_PASSWORD


User = get_user_model()


class AccessRevocationTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def grant_access(self):
        access, _ = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
        )
        return access

    def create_invitation(self, email="convidado@example.local"):
        _, invitation = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=email,
        )
        return invitation

    def test_grantor_revokes_immediately_and_preserves_history(self):
        access = self.grant_access()
        self.assertIn(self.contract, contracts_visible_to(self.other))

        revoke_contract_access(
            access_id=access.pk,
            contract_id=self.contract.pk,
            actor=self.owner,
        )

        access.refresh_from_db()
        self.assertEqual(access.status, ContractAccessStatus.REVOKED)
        self.assertEqual(access.revoked_by, self.owner)
        self.assertIsNotNone(access.revoked_at)
        self.assertEqual(access.granted_by, self.owner)
        self.assertNotIn(self.contract, contracts_visible_to(self.other))
        event = ContractSharingEvent.objects.get(
            event_type=ContractSharingEvent.EventType.ACCESS_REVOKED
        )
        self.assertEqual(event.access, access)
        self.assertEqual(event.actor, self.owner)

    def test_unrelated_fiscal_cannot_revoke_access(self):
        access = self.grant_access()
        with self.assertRaises(ContractAccess.DoesNotExist):
            revoke_contract_access(
                access_id=access.pk,
                contract_id=self.contract.pk,
                actor=self.other,
            )
        access.refresh_from_db()
        self.assertEqual(access.status, ContractAccessStatus.ACTIVE)

    def test_administrator_can_revoke_improper_access(self):
        access = self.grant_access()
        revoke_contract_access(
            access_id=access.pk,
            contract_id=self.contract.pk,
            actor=self.admin,
        )
        access.refresh_from_db()
        self.assertEqual(access.revoked_by, self.admin)
        self.assertNotIn(self.contract, contracts_visible_to(self.other))

    def test_revocation_requires_confirmation_and_cannot_repeat(self):
        access = self.grant_access()
        self.client.force_login(self.owner)
        url = reverse(
            "contracts:access_revoke", args=[self.contract.pk, access.pk]
        )
        confirmation = self.client.get(url)
        self.assertContains(confirmation, "Confirmar revogação")
        self.assertContains(confirmation, self.other.email)
        response = self.client.post(url)
        self.assertRedirects(
            response, reverse("contracts:access_list", args=[self.contract.pk])
        )
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cross_contract_url_cannot_revoke(self):
        access = self.grant_access()
        self.client.force_login(self.owner)
        url = reverse(
            "contracts:access_revoke", args=[self.contract.pk + 999999, access.pk]
        )
        self.assertEqual(self.client.post(url).status_code, 404)
        access.refresh_from_db()
        self.assertEqual(access.status, ContractAccessStatus.ACTIVE)

    def test_inviter_cancels_pending_invitation_with_audit(self):
        invitation = self.create_invitation()
        cancel_contract_invitation(
            invitation_id=invitation.pk,
            contract_id=self.contract.pk,
            actor=self.owner,
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ContractInvitationStatus.CANCELED)
        event = ContractSharingEvent.objects.get(
            event_type=ContractSharingEvent.EventType.INVITATION_CANCELED
        )
        self.assertEqual(event.invitation, invitation)
        self.assertEqual(event.actor, self.owner)

    def test_administrator_can_cancel_pending_invitation(self):
        invitation = self.create_invitation()
        cancel_contract_invitation(
            invitation_id=invitation.pk,
            contract_id=self.contract.pk,
            actor=self.admin,
        )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ContractInvitationStatus.CANCELED)

    def test_unrelated_fiscal_cannot_cancel_invitation(self):
        invitation = self.create_invitation()
        with self.assertRaises(type(invitation).DoesNotExist):
            cancel_contract_invitation(
                invitation_id=invitation.pk,
                contract_id=self.contract.pk,
                actor=self.other,
            )
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ContractInvitationStatus.PENDING)

    def test_canceled_invitation_is_not_accepted_when_account_is_created(self):
        email = "cancelado@example.local"
        invitation = self.create_invitation(email)
        cancel_contract_invitation(
            invitation_id=invitation.pk,
            contract_id=self.contract.pk,
            actor=self.owner,
        )
        user = User.objects.create_user(
            email=email,
            full_name="Convite Cancelado",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.assertFalse(
            ContractAccess.objects.filter(contract=self.contract, user=user).exists()
        )

    def test_access_list_exposes_only_allowed_actions(self):
        access = self.grant_access()
        invitation = self.create_invitation()
        self.client.force_login(self.owner)
        listing = self.client.get(
            reverse("contracts:access_list", args=[self.contract.pk])
        )
        self.assertContains(
            listing,
            reverse("contracts:access_revoke", args=[self.contract.pk, access.pk]),
        )
        self.assertContains(
            listing,
            reverse(
                "contracts:invitation_cancel",
                args=[self.contract.pk, invitation.pk],
            ),
        )
