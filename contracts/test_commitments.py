from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import BudgetCommitment, BudgetCommitmentEvent, CommitmentMovement
from .services import (
    create_budget_commitment,
    create_commitment_movement,
    create_contract,
    update_budget_commitment,
)
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


def commitment_data(**overrides):
    data = {
        "number": "2026NE000001",
        "ped": "2026PD000001",
        "commitment_date": date(2026, 9, 28),
        "initial_value": Decimal("100000.00"),
        "source": "Fonte institucional",
        "notes": "",
        "is_active": True,
    }
    data.update(overrides)
    return data


def movement_data(**overrides):
    data = {
        "movement_type": CommitmentMovement.Type.REINFORCEMENT,
        "movement_date": date(2026, 9, 28),
        "amount": Decimal("25000.00"),
        "notes": "Reforço registrado",
    }
    data.update(overrides)
    return data


class BudgetCommitmentModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização de Empenhos")
        self.fiscal = User.objects.create_user(
            email="modelo.empenho@example.local",
            full_name="Fiscal de Empenho",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.contract = create_contract(actor=self.fiscal, **contract_data())

    def create_commitment(self, **overrides):
        return create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            **commitment_data(**overrides),
        )

    def test_text_is_normalized_and_number_is_not_given_unproved_uniqueness(self):
        first = self.create_commitment(
            number="  2026NE000001  ",
            ped="  2026PD000001 ",
            source="  Fonte   institucional ",
        )
        second = self.create_commitment(number="2026NE000001")
        self.assertEqual(first.number, "2026NE000001")
        self.assertEqual(first.ped, "2026PD000001")
        self.assertEqual(first.source, "Fonte institucional")
        self.assertNotEqual(first.pk, second.pk)

    def test_current_value_uses_decimal_reinforcements_and_cancellations(self):
        commitment = self.create_commitment()
        create_commitment_movement(
            commitment_id=commitment.pk,
            actor=self.fiscal,
            **movement_data(amount=Decimal("25000.00")),
        )
        create_commitment_movement(
            commitment_id=commitment.pk,
            actor=self.fiscal,
            **movement_data(
                movement_type=CommitmentMovement.Type.CANCELLATION,
                amount=Decimal("10000.00"),
            ),
        )
        commitment.refresh_from_db()
        self.assertIsInstance(commitment.current_value, Decimal)
        self.assertEqual(commitment.current_value, Decimal("115000.00"))

    def test_nonpositive_movement_and_negative_current_value_are_rejected(self):
        commitment = self.create_commitment(initial_value=Decimal("100.00"))
        with self.assertRaises(ValidationError):
            create_commitment_movement(
                commitment_id=commitment.pk,
                actor=self.fiscal,
                **movement_data(amount=Decimal("0.00")),
            )
        with self.assertRaisesMessage(ValidationError, "não pode tornar"):
            create_commitment_movement(
                commitment_id=commitment.pk,
                actor=self.fiscal,
                **movement_data(
                    movement_type=CommitmentMovement.Type.CANCELLATION,
                    amount=Decimal("100.01"),
                ),
            )
        self.assertEqual(CommitmentMovement.objects.count(), 0)

    def test_fiscal_year_reversal_requires_official_document(self):
        commitment = self.create_commitment(initial_value=Decimal("100.00"))

        with self.assertRaisesMessage(ValidationError, "documento oficial"):
            create_commitment_movement(
                commitment_id=commitment.pk,
                actor=self.fiscal,
                **movement_data(
                    movement_type=CommitmentMovement.Type.REVERSAL,
                    movement_date=date(2026, 12, 31),
                    amount=Decimal("100.00"),
                    document_reference="",
                ),
            )

        self.assertEqual(CommitmentMovement.objects.count(), 0)

    def test_reversal_closes_old_commitment_and_new_year_is_separate(self):
        commitment = self.create_commitment(initial_value=Decimal("100.00"))
        reversal = create_commitment_movement(
            commitment_id=commitment.pk,
            actor=self.fiscal,
            **movement_data(
                movement_type=CommitmentMovement.Type.REVERSAL,
                movement_date=date(2026, 12, 31),
                amount=Decimal("100.00"),
                document_reference="DEMO-DOC-2026/ESTORNO-001",
            ),
        )
        commitment.refresh_from_db()
        following = self.create_commitment(
            number="2027NE000001",
            ped="2027PD000001",
            commitment_date=date(2027, 1, 10),
            initial_value=Decimal("200.00"),
        )

        self.assertEqual(reversal.document_reference, "DEMO-DOC-2026/ESTORNO-001")
        self.assertEqual(commitment.current_value, Decimal("0.00"))
        self.assertEqual(commitment.closed_for_new_allocations_at, date(2026, 12, 31))
        self.assertFalse(commitment.accepts_new_allocations)
        self.assertEqual(following.fiscal_year, 2027)
        self.assertEqual(following.current_value, Decimal("200.00"))

    def test_initial_value_cannot_be_changed_to_make_current_value_negative(self):
        commitment = self.create_commitment(initial_value=Decimal("100.00"))
        create_commitment_movement(
            commitment_id=commitment.pk,
            actor=self.fiscal,
            **movement_data(
                movement_type=CommitmentMovement.Type.CANCELLATION,
                amount=Decimal("80.00"),
            ),
        )
        with self.assertRaisesMessage(ValidationError, "tornaria o valor atual negativo"):
            update_budget_commitment(
                commitment_id=commitment.pk,
                actor=self.fiscal,
                **commitment_data(initial_value=Decimal("50.00")),
            )


class BudgetCommitmentAccessTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Financeira")
        self.owner = User.objects.create_user(
            email="dono.empenho@example.local",
            full_name="Fiscal Responsável por Empenho",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro.empenho@example.local",
            full_name="Outro Fiscal de Empenho",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.empenho@example.local",
            full_name="Administrador de Empenho",
            password=VALID_PASSWORD,
        )
        self.manager = User.objects.create_user(
            email="gestor.empenho@example.local",
            full_name="Gestor de Empenho",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(),
        )
        self.client = Client()

    def test_creation_and_movement_are_audited_with_before_and_after_values(self):
        created = BudgetCommitmentEvent.objects.get(
            event_type=BudgetCommitmentEvent.EventType.CREATED,
            commitment=self.commitment,
        )
        self.assertEqual(created.actor, self.owner)
        movement = create_commitment_movement(
            commitment_id=self.commitment.pk,
            actor=self.owner,
            **movement_data(),
        )
        event = BudgetCommitmentEvent.objects.get(
            event_type=BudgetCommitmentEvent.EventType.MOVEMENT_CREATED,
            commitment=self.commitment,
        )
        self.assertEqual(event.details["anterior"]["valor_atual_derivado"], "100000.00")
        self.assertEqual(event.details["atual"]["valor_atual_derivado"], "125000.00")
        self.assertEqual(event.details["movimentacao"]["movimentacao_id"], movement.pk)

    def test_owner_creates_commitment_and_movement_through_localized_forms(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:commitment_create", args=[self.contract.pk]),
            {
                "number": "2026NE000002",
                "ped": "2026PD000002",
                "commitment_date": "2026-09-28",
                "initial_value": "1.234,56",
                "source": "Fonte de teste",
                "notes": "",
                "is_active": "on",
            },
        )
        created = BudgetCommitment.objects.get(number="2026NE000002")
        self.assertRedirects(
            response,
            reverse("contracts:commitment_detail", args=[self.contract.pk, created.pk]),
        )
        self.assertEqual(created.initial_value, Decimal("1234.56"))
        movement_response = self.client.post(
            reverse(
                "contracts:commitment_movement_create",
                args=[self.contract.pk, created.pk],
            ),
            {
                "movement_type": CommitmentMovement.Type.REINFORCEMENT,
                "movement_date": "2026-09-28",
                "amount": "100,44",
                "notes": "",
            },
        )
        self.assertRedirects(
            movement_response,
            reverse("contracts:commitment_detail", args=[self.contract.pk, created.pk]),
        )
        self.assertEqual(created.movements.get().amount, Decimal("100.44"))

    def test_other_fiscal_cannot_discover_or_move_commitment(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(
                reverse("contracts:commitment_list", args=[self.contract.pk])
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "contracts:commitment_detail",
                    args=[self.contract.pk, self.commitment.pk],
                )
            ).status_code,
            404,
        )
        with self.assertRaises(BudgetCommitment.DoesNotExist):
            create_commitment_movement(
                commitment_id=self.commitment.pk,
                actor=self.other,
                **movement_data(),
            )

    def test_administrator_reads_but_cannot_create_edit_or_move(self):
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse("contracts:commitment_list", args=[self.contract.pk])
        )
        self.assertContains(response, self.commitment.number)
        detail = self.client.get(
            reverse(
                "contracts:commitment_detail",
                args=[self.contract.pk, self.commitment.pk],
            )
        )
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, "Editar empenho")
        self.assertNotContains(detail, "Registrar reforço")
        self.assertEqual(
            self.client.get(
                reverse("contracts:commitment_create", args=[self.contract.pk])
            ).status_code,
            403,
        )

    def test_inactive_commitment_rejects_new_movement_and_preserves_history(self):
        commitment = update_budget_commitment(
            commitment_id=self.commitment.pk,
            actor=self.owner,
            **commitment_data(is_active=False),
        )
        self.assertFalse(commitment.is_active)
        with self.assertRaises(BudgetCommitment.DoesNotExist):
            create_commitment_movement(
                commitment_id=commitment.pk,
                actor=self.owner,
                **movement_data(),
            )
        self.assertTrue(BudgetCommitment.objects.filter(pk=commitment.pk).exists())
        self.assertTrue(
            BudgetCommitmentEvent.objects.filter(
                commitment=commitment,
                event_type=BudgetCommitmentEvent.EventType.DEACTIVATED,
                actor=self.owner,
            ).exists()
        )

    def test_permissions_and_admin_are_read_only_and_movements_have_no_edit_route(self):
        self.assertTrue(self.owner.has_perm("contracts.add_budgetcommitment"))
        self.assertTrue(self.owner.has_perm("contracts.add_commitmentmovement"))
        self.assertTrue(self.manager.has_perm("contracts.view_budgetcommitment"))
        self.assertFalse(self.manager.has_perm("contracts.add_budgetcommitment"))
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_budgetcommitment_add")).status_code,
            403,
        )
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("commitment_delete", route_names)
        self.assertNotIn("commitment_movement_update", route_names)
        self.assertNotIn("commitment_movement_delete", route_names)
