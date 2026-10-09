from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import DatabaseError, close_old_connections, connection
from django.test import TransactionTestCase

from accounts.models import AccountStatus
from organizations.models import Organization

from .models import (
    CommitmentMovement,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderAllocation,
    WorkOrderAllocationStatus,
    WorkOrderStatus,
)
from .services import (
    cancel_work_order_allocation,
    commitment_financial_position,
    create_budget_commitment,
    create_commitment_movement,
    create_contract,
    create_contract_item,
    create_invoice,
    create_payment,
    create_work_order,
    create_work_order_allocation,
    update_work_order_allocation,
)
from .test_invoices import invoice_data
from .test_payments import payment_data
from .test_commitments import commitment_data, movement_data
from .test_items import item_data
from .test_work_orders import work_order_data
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


class FinancialConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        if connection.vendor != "postgresql":
            self.skipTest("A concorrência financeira exige PostgreSQL real.")
        self.organization = Organization.objects.create(name="Organização Concorrência")
        self.owner = User.objects.create_user(
            email="concorrencia@example.local",
            full_name="Fiscal de Concorrência",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.contract = create_contract(
            actor=self.owner,
            **contract_data(original_value=Decimal("20000.00")),
        )
        self.item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(
                contracted_quantity=Decimal("100.0000"),
                unit_value=Decimal("250.00"),
            ),
        )
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )

    def run_simultaneously(self, *operations):
        barrier = Barrier(len(operations))

        def invoke(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return ("ok", operation())
            except Exception as error:  # resultado inspecionado pelo teste
                return ("error", error)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(operations)) as executor:
            futures = [executor.submit(invoke, operation) for operation in operations]
            return [future.result(timeout=20) for future in futures]

    def actor(self):
        return User.objects.get(pk=self.owner.pk)

    def commitment_record(self):
        return type(self.commitment).objects.get(pk=self.commitment.pk)

    def create_order(self, *, number, hours):
        return create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(
                self.item,
                number=number,
                hours=hours,
                status=WorkOrderStatus.SIGNED,
            ),
        )

    def allocation_operation(self, *, work_order_id, amount):
        def operation():
            allocation = create_work_order_allocation(
                work_order_id=work_order_id,
                actor=self.actor(),
                commitment=self.commitment_record(),
                amount=amount,
                allocation_date=date(2026, 9, 29),
                status=WorkOrderAllocationStatus.ACTIVE,
            )
            return allocation.pk

        return operation

    def assert_no_database_error(self, results):
        database_errors = [
            error
            for status, error in results
            if status == "error" and isinstance(error, DatabaseError)
        ]
        self.assertEqual(database_errors, [], database_errors)

    def test_simultaneous_allocations_never_overspend_same_commitment(self):
        first_order = self.create_order(number="OS-CONCORRENTE-1", hours=Decimal("28.0000"))
        second_order = self.create_order(number="OS-CONCORRENTE-2", hours=Decimal("28.0000"))

        results = self.run_simultaneously(
            self.allocation_operation(
                work_order_id=first_order.pk, amount=Decimal("7000.00")
            ),
            self.allocation_operation(
                work_order_id=second_order.pk, amount=Decimal("7000.00")
            ),
        )

        self.assert_no_database_error(results)
        self.assertEqual([status for status, _ in results].count("ok"), 1)
        errors = [error for status, error in results if status == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)
        self.assertIn("saldo disponível", str(errors[0]))
        self.assertEqual(WorkOrderAllocation.objects.count(), 1)
        self.assertEqual(
            commitment_financial_position(self.commitment_record()).available_balance.value,
            Decimal("3000.00"),
        )

    def test_allocation_and_cancellation_movement_are_serialized(self):
        first_order = self.create_order(number="OS-BASE", hours=Decimal("16.0000"))
        second_order = self.create_order(number="OS-DISPUTA", hours=Decimal("24.0000"))
        create_work_order_allocation(
            work_order_id=first_order.pk,
            actor=self.owner,
            commitment=self.commitment,
            amount=Decimal("4000.00"),
            allocation_date=date(2026, 9, 29),
            status=WorkOrderAllocationStatus.ACTIVE,
        )

        def cancellation_operation():
            movement = create_commitment_movement(
                commitment_id=self.commitment.pk,
                actor=self.actor(),
                **movement_data(
                    movement_type=CommitmentMovement.Type.CANCELLATION,
                    amount=Decimal("4000.00"),
                ),
            )
            return movement.pk

        results = self.run_simultaneously(
            self.allocation_operation(
                work_order_id=second_order.pk, amount=Decimal("6000.00")
            ),
            cancellation_operation,
        )

        self.assert_no_database_error(results)
        self.assertEqual([status for status, _ in results].count("ok"), 1)
        self.assertEqual([status for status, _ in results].count("error"), 1)
        position = commitment_financial_position(self.commitment_record())
        self.assertGreaterEqual(position.available_balance.value, Decimal("0.00"))

    def test_simultaneous_orders_never_overspend_contract(self):
        def order_operation(number):
            def operation():
                order = create_work_order(
                    contract_id=self.contract.pk,
                    actor=self.actor(),
                    **work_order_data(
                        type(self.item).objects.get(pk=self.item.pk),
                        number=number,
                        hours=Decimal("48.0000"),
                        status=WorkOrderStatus.SIGNED,
                    ),
                )
                return order.pk

            return operation

        results = self.run_simultaneously(
            order_operation("OS-LIMITE-1"),
            order_operation("OS-LIMITE-2"),
        )

        self.assert_no_database_error(results)
        self.assertEqual([status for status, _ in results].count("ok"), 1)
        self.assertEqual(WorkOrder.objects.count(), 1)
        self.assertEqual(WorkOrder.objects.get().total_value, Decimal("12000.00"))

    def test_cancel_and_update_same_allocation_do_not_deadlock(self):
        order = self.create_order(number="OS-CANCELAMENTO", hours=Decimal("40.0000"))
        allocation = create_work_order_allocation(
            work_order_id=order.pk,
            actor=self.owner,
            commitment=self.commitment,
            amount=Decimal("4000.00"),
            allocation_date=date(2026, 9, 29),
            status=WorkOrderAllocationStatus.ACTIVE,
        )

        def update_operation():
            updated = update_work_order_allocation(
                allocation_id=allocation.pk,
                actor=self.actor(),
                commitment=self.commitment_record(),
                amount=Decimal("5000.00"),
                allocation_date=date(2026, 9, 29),
                status=WorkOrderAllocationStatus.ACTIVE,
            )
            return updated.pk

        def cancel_operation():
            canceled = cancel_work_order_allocation(
                allocation_id=allocation.pk,
                actor=self.actor(),
                reason="Cancelamento concorrente controlado",
            )
            return canceled.pk

        results = self.run_simultaneously(update_operation, cancel_operation)

        self.assert_no_database_error(results)
        allocation.refresh_from_db()
        self.assertEqual(allocation.status, WorkOrderAllocationStatus.CANCELED)
        self.assertEqual(WorkOrderAllocation.objects.count(), 1)

    def test_simultaneous_invoices_never_exceed_work_order_value(self):
        order = self.create_order(number="OS-NF-CONCORRENTE", hours=Decimal("40.0000"))

        def invoice_operation(number):
            def operation():
                current_contract = type(self.contract).objects.get(pk=self.contract.pk)
                invoice = create_invoice(
                    work_order_id=order.pk,
                    actor=self.actor(),
                    **invoice_data(
                        current_contract,
                        number=number,
                        gross_value=Decimal("6000.00"),
                        accepted_value=Decimal("6000.00"),
                    ),
                )
                return invoice.pk

            return operation

        results = self.run_simultaneously(
            invoice_operation("NF-CONCORRENTE-1"),
            invoice_operation("NF-CONCORRENTE-2"),
        )

        self.assert_no_database_error(results)
        self.assertEqual([status for status, _ in results].count("ok"), 1)
        errors = [error for status, error in results if status == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)
        self.assertIn("ultrapassa", str(errors[0]))
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(
            sum(Invoice.objects.values_list("gross_value", flat=True), Decimal("0.00")),
            Decimal("6000.00"),
        )

    def test_simultaneous_payments_never_exceed_invoice_limit(self):
        order = self.create_order(number="OS-PAG-CONCORRENTE", hours=Decimal("40.0000"))
        invoice = create_invoice(
            work_order_id=order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                number="NF-PAG-CONCORRENTE",
                gross_value=Decimal("10000.00"),
                accepted_value=Decimal("10000.00"),
            ),
        )

        def payment_operation(process_number):
            def operation():
                payment = create_payment(
                    invoice_id=invoice.pk,
                    actor=self.actor(),
                    **payment_data(
                        amount=Decimal("6000.00"), process_number=process_number
                    ),
                )
                return payment.pk

            return operation

        results = self.run_simultaneously(
            payment_operation("PROC-PAG-CONCORRENTE-1"),
            payment_operation("PROC-PAG-CONCORRENTE-2"),
        )

        self.assert_no_database_error(results)
        self.assertEqual([status for status, _ in results].count("ok"), 1)
        errors = [error for status, error in results if status == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)
        self.assertIn("ultrapassa", str(errors[0]))
        self.assertEqual(Payment.objects.count(), 1)
