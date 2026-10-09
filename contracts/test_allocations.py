from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse

from .models import (
    WorkOrderAllocation,
    WorkOrderAllocationEvent,
    WorkOrderAllocationStatus,
    WorkOrderStatus,
    CommitmentMovement,
)
from .services import (
    cancel_work_order,
    cancel_work_order_allocation,
    commitment_financial_position,
    create_budget_commitment,
    create_contract,
    create_commitment_movement,
    create_work_order_allocation,
    update_budget_commitment,
    update_work_order,
    update_work_order_allocation,
)
from .test_commitments import commitment_data, movement_data
from .test_work_orders import WorkOrderBase, work_order_data
from .tests import contract_data


class WorkOrderAllocationTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.SIGNED
        )

    def allocation_data(self, **overrides):
        data = {
            "commitment": self.commitment,
            "amount": Decimal("6000.00"),
            "allocation_date": date(2026, 9, 29),
            "status": WorkOrderAllocationStatus.ACTIVE,
        }
        data.update(overrides)
        return data

    def create_allocation(self, **overrides):
        return create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            **self.allocation_data(**overrides),
        )

    def test_two_commitments_can_complete_order_exactly(self):
        second = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(number="2026NE000002", initial_value=Decimal("4000.00")),
        )
        first = self.create_allocation()
        other = self.create_allocation(commitment=second, amount=Decimal("4000.00"))
        total = sum(
            (allocation.amount for allocation in self.order.allocations.all()),
            Decimal("0.00"),
        )
        self.assertEqual(total, self.order.total_value)
        self.assertEqual(first.status, WorkOrderAllocationStatus.ACTIVE)
        self.assertEqual(other.created_by, self.owner)

    def test_reversal_must_equal_available_balance_and_blocks_new_allocations(self):
        self.create_allocation(amount=Decimal("6000.00"))
        with self.assertRaisesMessage(ValidationError, "exatamente ao saldo disponível"):
            create_commitment_movement(
                commitment_id=self.commitment.pk,
                actor=self.owner,
                **movement_data(
                    movement_type=CommitmentMovement.Type.REVERSAL,
                    movement_date=date(2026, 12, 31),
                    amount=Decimal("3000.00"),
                    document_reference="DEMO-DOC-2026/ESTORNO-INCORRETO",
                ),
            )

        reversal = create_commitment_movement(
            commitment_id=self.commitment.pk,
            actor=self.owner,
            **movement_data(
                movement_type=CommitmentMovement.Type.REVERSAL,
                movement_date=date(2026, 12, 31),
                amount=Decimal("4000.00"),
                document_reference="DEMO-DOC-2026/ESTORNO-001",
            ),
        )
        self.commitment.refresh_from_db()
        self.assertEqual(reversal.amount, Decimal("4000.00"))
        self.assertEqual(self.commitment.current_value, Decimal("6000.00"))
        self.assertEqual(
            self.commitment.closed_for_new_allocations_at,
            date(2026, 12, 31),
        )
        with self.assertRaisesMessage(ValidationError, "encerrado por estorno"):
            self.create_allocation(amount=Decimal("1000.00"))

    def test_zero_cross_contract_and_total_above_order_are_blocked(self):
        with self.assertRaisesMessage(ValidationError, "maior que zero"):
            self.create_allocation(amount=Decimal("0.00"))
        second_contract = create_contract(
            actor=self.owner,
            **contract_data(number="038/2026", process_number="PROCESSO-038"),
        )
        foreign = create_budget_commitment(
            contract_id=second_contract.pk,
            actor=self.owner,
            **commitment_data(number="2026NE-FORA"),
        )
        with self.assertRaises(type(foreign).DoesNotExist):
            self.create_allocation(commitment=foreign)
        self.create_allocation(amount=Decimal("9000.00"))
        with self.assertRaisesMessage(ValidationError, "R$ 1,00"):
            self.create_allocation(amount=Decimal("1001.00"))

    def test_commitment_balance_is_protected_conservatively(self):
        self.create_allocation(amount=Decimal("9000.00"))
        second_order = self.create_work_order(
            number="OS-002", hours=Decimal("8.0000"), status=WorkOrderStatus.OPEN
        )
        with self.assertRaisesMessage(ValidationError, "R$ 1,00"):
            create_work_order_allocation(
                work_order_id=second_order.pk,
                actor=self.owner,
                **self.allocation_data(amount=Decimal("1001.00")),
            )

    def test_financial_position_counts_only_active_confirmed_os_allocation(self):
        allocation = self.create_allocation()
        position = commitment_financial_position(self.commitment)
        self.assertEqual(position.committed_value.value, Decimal("6000.00"))
        self.assertEqual(position.available_balance.value, Decimal("4000.00"))
        self.assertEqual(position.committed_value.evidence[0].source_type, "RATEIO_OS")
        update_work_order_allocation(
            allocation_id=allocation.pk,
            actor=self.owner,
            **self.allocation_data(status=WorkOrderAllocationStatus.INACTIVE),
        )
        self.assertEqual(
            commitment_financial_position(self.commitment).committed_value.value,
            Decimal("0.00"),
        )

    def test_open_os_is_reserved_but_not_classified_as_committed(self):
        self.order.status = WorkOrderStatus.OPEN
        self.order.save()
        self.create_allocation()
        position = commitment_financial_position(self.commitment)
        self.assertEqual(position.committed_value.value, Decimal("0.00"))
        second_order = self.create_work_order(
            number="OS-OPEN-2", hours=Decimal("20.0000"), status=WorkOrderStatus.OPEN
        )
        with self.assertRaisesMessage(ValidationError, "saldo disponível"):
            create_work_order_allocation(
                work_order_id=second_order.pk,
                actor=self.owner,
                **self.allocation_data(amount=Decimal("4001.00")),
            )

    def test_update_activation_and_cancel_are_audited(self):
        allocation = self.create_allocation(status=WorkOrderAllocationStatus.INACTIVE)
        allocation = update_work_order_allocation(
            allocation_id=allocation.pk,
            actor=self.owner,
            **self.allocation_data(amount=Decimal("5000.00")),
        )
        self.assertEqual(allocation.status, WorkOrderAllocationStatus.ACTIVE)
        self.assertTrue(
            allocation.events.filter(
                event_type=WorkOrderAllocationEvent.EventType.ACTIVATED
            ).exists()
        )
        canceled = cancel_work_order_allocation(
            allocation_id=allocation.pk,
            actor=self.owner,
            reason="  Ajuste   formal do rateio  ",
        )
        self.assertEqual(canceled.status, WorkOrderAllocationStatus.CANCELED)
        self.assertEqual(canceled.cancellation_reason, "Ajuste formal do rateio")
        with self.assertRaisesMessage(ValidationError, "somente leitura"):
            update_work_order_allocation(
                allocation_id=allocation.pk,
                actor=self.owner,
                **self.allocation_data(),
            )

    def test_canceling_order_deactivates_active_allocation_and_preserves_it(self):
        allocation = self.create_allocation()
        cancel_work_order(
            work_order_id=self.order.pk,
            actor=self.owner,
            reason="Cancelamento formal da OS",
        )
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, WorkOrderAllocationStatus.INACTIVE)
        self.assertTrue(WorkOrderAllocation.objects.filter(pk=allocation.pk).exists())
        self.assertEqual(
            commitment_financial_position(self.commitment).committed_value.value,
            Decimal("0.00"),
        )

    def test_order_and_commitment_cannot_be_reduced_below_active_allocations(self):
        self.create_allocation(amount=Decimal("6000.00"))
        with self.assertRaisesMessage(ValidationError, "abaixo dos rateios ativos"):
            update_work_order(
                work_order_id=self.order.pk,
                actor=self.owner,
                **work_order_data(
                    self.item,
                    number=self.order.number,
                    hours=Decimal("20.0000"),
                    status=WorkOrderStatus.SIGNED,
                ),
            )
        with self.assertRaisesMessage(ValidationError, "rateio ativo"):
            update_budget_commitment(
                commitment_id=self.commitment.pk,
                actor=self.owner,
                **commitment_data(initial_value=Decimal("10000.00"), is_active=False),
            )
        with self.assertRaisesMessage(ValidationError, "abaixo dos rateios ativos"):
            update_budget_commitment(
                commitment_id=self.commitment.pk,
                actor=self.owner,
                **commitment_data(initial_value=Decimal("5000.00")),
            )
        with self.assertRaisesMessage(ValidationError, "saldo protegido"):
            create_commitment_movement(
                commitment_id=self.commitment.pk,
                actor=self.owner,
                **movement_data(
                    movement_type=CommitmentMovement.Type.CANCELLATION,
                    amount=Decimal("5000.00"),
                ),
            )

    def test_owner_web_form_localizes_amount_and_other_fiscal_is_hidden(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:allocation_create", args=[self.contract.pk, self.order.pk]),
            {
                "commitment": self.commitment.pk,
                "amount": "1.234,56",
                "allocation_date": "2026-09-29",
                "status": WorkOrderAllocationStatus.ACTIVE,
            },
        )
        allocation = WorkOrderAllocation.objects.get()
        self.assertRedirects(
            response,
            reverse("contracts:work_order_detail", args=[self.contract.pk, self.order.pk]),
        )
        self.assertEqual(allocation.amount, Decimal("1234.56"))
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(
                reverse("contracts:allocation_update", args=[self.contract.pk, self.order.pk, allocation.pk])
            ).status_code,
            404,
        )

    def test_permissions_admin_read_only_and_no_delete_route(self):
        self.assertTrue(self.owner.has_perm("contracts.add_workorderallocation"))
        self.assertTrue(self.owner.has_perm("contracts.change_workorderallocation"))
        self.assertTrue(self.manager.has_perm("contracts.view_workorderallocation"))
        self.assertFalse(self.manager.has_perm("contracts.add_workorderallocation"))
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_workorderallocation_add")).status_code,
            403,
        )
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("allocation_delete", route_names)
