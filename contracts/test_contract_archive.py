from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus
from organizations.models import Organization

from .models import Contract, ContractEvent, ContractStatus
from .services import (
    archive_contract,
    archived_contracts_managed_by,
    contracts_visible_to,
    contracts_writable_by,
    create_contract,
    create_contract_item,
    restore_archived_contract,
    share_contract_read_only,
    update_contract,
)
from .test_items import item_data
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


class ContractArchiveTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Arquivamento")
        self.owner = User.objects.create_user(
            email="titular.arquivo@example.local",
            full_name="Fiscal Titular",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro.arquivo@example.local",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.arquivo@example.local",
            full_name="Administrador Arquivamento",
            password=VALID_PASSWORD,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.client = Client()

    def archive(self, actor=None):
        return archive_contract(
            contract_id=self.contract.pk,
            actor=actor or self.owner,
            reason="Contrato cadastrado em duplicidade por engano.",
            confirmed=True,
        )

    def test_logical_archive_hides_contract_without_deleting_history(self):
        contract_pk = self.contract.pk
        self.archive()
        self.contract.refresh_from_db()

        self.assertIsNotNone(self.contract.archived_at)
        self.assertEqual(self.contract.archived_by, self.owner)
        self.assertEqual(Contract.objects.filter(pk=contract_pk).count(), 1)
        self.assertNotIn(self.contract, contracts_visible_to(self.owner))
        self.assertNotIn(self.contract, contracts_writable_by(self.owner))
        self.assertIn(self.contract, archived_contracts_managed_by(self.owner))
        event = ContractEvent.objects.get(
            contract=self.contract,
            event_type=ContractEvent.EventType.ARCHIVED,
        )
        self.assertFalse(event.details["exclusao_fisica"])

        self.client.force_login(self.owner)
        self.assertNotContains(self.client.get(reverse("contracts:list")), "001/2099")
        self.assertContains(
            self.client.get(reverse("contracts:archived_list")),
            "Contrato cadastrado em duplicidade",
        )
        self.assertEqual(
            self.client.get(reverse("contracts:detail", args=[contract_pk])).status_code,
            404,
        )

    def test_restore_returns_contract_to_same_owner_and_status(self):
        self.contract.status = ContractStatus.SUSPENDED
        self.contract.save(update_fields=("status", "updated_at"))
        self.archive()
        restored = restore_archived_contract(
            contract_id=self.contract.pk,
            actor=self.owner,
            reason="Revisão confirmou que o cadastro é válido.",
            confirmed=True,
        )
        self.assertIsNone(restored.archived_at)
        self.assertEqual(restored.archive_reason, "")
        self.assertEqual(restored.status, ContractStatus.SUSPENDED)
        self.assertEqual(restored.responsible_fiscal, self.owner)
        self.assertIn(restored, contracts_visible_to(self.owner))
        self.assertTrue(
            ContractEvent.objects.filter(
                contract=restored,
                event_type=ContractEvent.EventType.RESTORED,
            ).exists()
        )

    def test_archive_requires_confirmation_and_reason(self):
        with self.assertRaisesMessage(ValidationError, "Confirme expressamente"):
            archive_contract(
                contract_id=self.contract.pk,
                actor=self.owner,
                reason="Motivo válido",
                confirmed=False,
            )
        with self.assertRaisesMessage(ValidationError, "justificativa"):
            archive_contract(
                contract_id=self.contract.pk,
                actor=self.owner,
                reason="  ",
                confirmed=True,
            )

    def test_operational_history_blocks_archive_and_structural_changes(self):
        create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(),
        )
        with self.assertRaisesMessage(ValidationError, "itens"):
            self.archive()
        with self.assertRaisesMessage(ValidationError, "Campos estruturais"):
            update_contract(
                contract_id=self.contract.pk,
                actor=self.owner,
                **contract_data(original_value=Decimal("120000.00")),
            )

        updated = update_contract(
            contract_id=self.contract.pk,
            actor=self.owner,
            **contract_data(
                status=ContractStatus.SUSPENDED,
                notes="Suspensão registrada sem alterar a identidade.",
            ),
        )
        self.assertEqual(updated.status, ContractStatus.SUSPENDED)
        self.assertEqual(
            updated.notes, "Suspensão registrada sem alterar a identidade."
        )

    def test_active_access_blocks_archive_but_revoked_history_does_not(self):
        access, _ = share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
        )
        with self.assertRaisesMessage(ValidationError, "Somente leitura"):
            self.archive()
        access.status = "REVOGADO"
        access.revoked_by = self.owner
        from django.utils import timezone

        access.revoked_at = timezone.now()
        access.save(update_fields=("status", "revoked_by", "revoked_at"))
        self.archive()
        self.contract.refresh_from_db()
        self.assertIsNotNone(self.contract.archived_at)

    def test_physical_delete_is_always_rejected(self):
        with self.assertRaisesMessage(ValidationError, "não pode ser excluído fisicamente"):
            self.contract.delete()
        self.assertTrue(Contract.objects.filter(pk=self.contract.pk).exists())

    def test_other_fiscal_cannot_archive_restore_or_discover_archived_contract(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:archive", args=[self.contract.pk])).status_code,
            403,
        )
        self.archive()
        self.assertNotIn(self.contract, archived_contracts_managed_by(self.other))
        self.assertEqual(
            self.client.get(reverse("contracts:restore", args=[self.contract.pk])).status_code,
            403,
        )

    def test_administrator_can_archive_contract_of_inactive_fiscal(self):
        self.owner.status = AccountStatus.INACTIVE
        self.owner.is_active = False
        self.owner.save(update_fields=("status", "is_active"))
        archived = self.archive(actor=self.admin)
        self.assertEqual(archived.archived_by, self.admin)
        self.assertIn(archived, archived_contracts_managed_by(self.admin))

    def test_archive_event_remains_immutable_in_postgresql(self):
        self.archive()
        event = ContractEvent.objects.get(
            contract=self.contract,
            event_type=ContractEvent.EventType.ARCHIVED,
        )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                ContractEvent.objects.filter(pk=event.pk).update(details={"alterado": True})
