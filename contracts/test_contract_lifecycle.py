from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import (
    ContractEvent,
    ContractStatus,
    FiscalSubstitutionStatus,
    WorkOrderStatus,
)
from .services import (
    close_contract,
    contracts_visible_to,
    contracts_writable_by,
    create_fiscal_substitution,
    transfer_contract_responsibility,
    update_contract,
)
from .test_work_orders import WorkOrderBase
from .tests import VALID_PASSWORD, contract_data


class ContractLifecycleTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.client = Client()

    def close(self, actor=None):
        return close_contract(
            contract_id=self.contract.pk,
            actor=actor or self.owner,
            reason="Execução contratual concluída e conferida.",
            confirmed=True,
        )

    def test_close_preserves_read_access_and_blocks_every_new_write(self):
        self.close()
        self.contract.refresh_from_db()

        self.assertEqual(self.contract.status, ContractStatus.CLOSED)
        self.assertIsNotNone(self.contract.closed_at)
        self.assertEqual(self.contract.closed_by, self.owner)
        self.assertIn(self.contract, contracts_visible_to(self.owner))
        self.assertNotIn(self.contract, contracts_writable_by(self.owner))
        event = ContractEvent.objects.get(
            contract=self.contract,
            event_type=ContractEvent.EventType.CLOSED,
        )
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(
            event.details["justificativa"],
            "Execução contratual concluída e conferida.",
        )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertContains(response, "Contrato encerrado")
        self.assertContains(response, "Execução contratual concluída")
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )

    def test_close_requires_confirmation_reason_and_terminal_work_orders(self):
        with self.assertRaisesMessage(ValidationError, "Confirme expressamente"):
            close_contract(
                contract_id=self.contract.pk,
                actor=self.owner,
                reason="Motivo válido",
                confirmed=False,
            )
        with self.assertRaisesMessage(ValidationError, "justificativa"):
            close_contract(
                contract_id=self.contract.pk,
                actor=self.owner,
                reason="   ",
                confirmed=True,
            )

        self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        with self.assertRaisesMessage(ValidationError, "Ordens de Serviço"):
            self.close()
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, ContractStatus.ACTIVE)

    def test_closed_and_canceled_statuses_cannot_be_selected_in_common_edit(self):
        for forbidden_status in (ContractStatus.CLOSED, ContractStatus.CANCELED):
            with self.subTest(status=forbidden_status):
                with self.assertRaisesMessage(ValidationError, "fluxo formal"):
                    update_contract(
                        contract_id=self.contract.pk,
                        actor=self.owner,
                        **contract_data(status=forbidden_status),
                    )

        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:update", args=[self.contract.pk]))
        self.assertNotContains(response, "Encerrado")
        self.assertNotContains(response, "Cancelado")

    def test_close_revokes_active_or_pending_substitutions(self):
        today = timezone.localdate()
        linked = create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
            starts_on=today,
            ends_on=today + timedelta(days=5),
        )
        self.close()
        linked.refresh_from_db()
        self.assertEqual(linked.status, FiscalSubstitutionStatus.REVOKED)
        self.assertEqual(linked.revoked_by, self.owner)
        self.assertNotIn(self.contract, contracts_writable_by(self.other))

    def test_transfer_changes_owner_and_records_audit(self):
        transferred = transfer_contract_responsibility(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email.upper(),
            reason="Redistribuição formal da fiscalização.",
            confirmed=True,
        )
        self.assertEqual(transferred.responsible_fiscal, self.other)
        self.assertNotIn(self.contract, contracts_visible_to(self.owner))
        self.assertIn(self.contract, contracts_visible_to(self.other))
        self.assertIn(self.contract, contracts_writable_by(self.other))
        event = ContractEvent.objects.get(
            contract=self.contract,
            event_type=ContractEvent.EventType.RESPONSIBLE_TRANSFERRED,
        )
        self.assertEqual(event.details["fiscal_anterior_id"], self.owner.pk)
        self.assertEqual(event.details["novo_fiscal_id"], self.other.pk)

    def test_transfer_rejects_self_inactive_consultation_and_other_organization(self):
        invalid_users = [
            self.owner,
            self._create_user(
                "inativo@example.local",
                status=AccountStatus.INACTIVE,
            ),
            self._create_user(
                "consulta@example.local",
                profile=UserProfile.CONSULTATION,
            ),
            self._create_user(
                "outra.organizacao@example.local",
                organization=Organization.objects.create(name="Outra organização"),
            ),
        ]
        for user in invalid_users:
            with self.subTest(email=user.email):
                with self.assertRaises(ValidationError):
                    transfer_contract_responsibility(
                        contract_id=self.contract.pk,
                        actor=self.owner,
                        email=user.email,
                        reason="Tentativa controlada.",
                        confirmed=True,
                    )

    def _create_user(
        self,
        email,
        *,
        profile=UserProfile.FISCAL,
        status=AccountStatus.ACTIVE,
        organization=None,
    ):
        return self.owner.__class__.objects.create_user(
            email=email,
            full_name=email,
            password=VALID_PASSWORD,
            profile=profile,
            status=status,
            organization=organization or self.organization,
        )

    def test_administrator_can_transfer_contract_from_inactive_owner(self):
        self.owner.status = AccountStatus.INACTIVE
        self.owner.is_active = False
        self.owner.save(update_fields=("status", "is_active"))
        transferred = transfer_contract_responsibility(
            contract_id=self.contract.pk,
            actor=self.admin,
            email=self.other.email,
            reason="Fiscal anterior desligado da instituição.",
            confirmed=True,
        )
        self.assertEqual(transferred.responsible_fiscal, self.other)

    def test_transfer_revokes_substitution_and_web_requires_confirmation(self):
        today = timezone.localdate()
        third = self._create_user("terceiro@example.local")
        substitution = create_fiscal_substitution(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=third.email,
            starts_on=today,
            ends_on=today + timedelta(days=5),
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:transfer", args=[self.contract.pk]),
            {
                "email": self.other.email,
                "reason": "Mudança formal do Fiscal responsável.",
                "confirmed": "on",
            },
        )
        self.assertRedirects(response, reverse("contracts:list"))
        substitution.refresh_from_db()
        self.assertEqual(substitution.status, FiscalSubstitutionStatus.REVOKED)
        self.assertNotIn(self.contract, contracts_writable_by(third))

    def test_non_owner_cannot_open_lifecycle_forms(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:close", args=[self.contract.pk])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse("contracts:transfer", args=[self.contract.pk])).status_code,
            403,
        )
