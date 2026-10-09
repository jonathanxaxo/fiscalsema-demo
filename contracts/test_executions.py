from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import WorkOrderExecution, WorkOrderExecutionEvent, WorkOrderStatus
from .services import (
    contract_financial_position,
    create_contract,
    create_contract_item,
    create_work_order,
    create_work_order_execution,
    item_financial_position,
    update_work_order,
    update_work_order_execution,
)
from .test_items import item_data
from .test_work_orders import work_order_data
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


def execution_data(**overrides):
    data = {
        "executed_quantity": Decimal("10.0000"),
        "executed_value": Decimal("2500.00"),
        "execution_date": date(2026, 9, 29),
        "competence": "09/2026",
        "notes": "Execução comprovada",
        "evidence_reference": "Relatório técnico 01",
    }
    data.update(overrides)
    return data


class WorkOrderExecutionTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Execução")
        self.owner = User.objects.create_user(
            email="execucao@example.local", full_name="Fiscal de Execução",
            password=VALID_PASSWORD, status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro.execucao@example.local", full_name="Outro Fiscal",
            password=VALID_PASSWORD, status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_user(
            email="admin.execucao@example.local", full_name="Administrador",
            password=VALID_PASSWORD, profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.item = create_contract_item(
            contract_id=self.contract.pk, actor=self.owner,
            **item_data(contracted_quantity=Decimal("100.0000"), unit_value=Decimal("250.00")),
        )
        self.order = create_work_order(
            contract_id=self.contract.pk, actor=self.owner,
            **work_order_data(self.item, hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS),
        )
        self.client = Client()

    def create_execution(self, **overrides):
        return create_work_order_execution(
            work_order_id=self.order.pk, actor=self.owner, **execution_data(**overrides)
        )

    def test_create_preserves_distinct_fields_and_audit(self):
        execution = self.create_execution()
        self.assertEqual(execution.executed_quantity, Decimal("10.0000"))
        self.assertEqual(execution.executed_value, Decimal("2500.00"))
        self.assertEqual(execution.competence, "09/2026")
        event = WorkOrderExecutionEvent.objects.get(execution=execution)
        self.assertEqual(event.event_type, WorkOrderExecutionEvent.EventType.CREATED)
        self.assertEqual(event.details["atual"]["valor_executado"], "2500.00")

    def test_positive_values_and_competence_are_validated(self):
        with self.assertRaises(ValidationError):
            self.create_execution(executed_quantity=Decimal("0"))
        with self.assertRaises(ValidationError):
            self.create_execution(executed_value=Decimal("0.00"))
        with self.assertRaisesMessage(ValidationError, "MM/AAAA"):
            self.create_execution(competence="13/2026")

    def test_cumulative_execution_cannot_exceed_order(self):
        self.create_execution(executed_quantity=Decimal("30.0000"), executed_value=Decimal("7000.00"))
        with self.assertRaisesMessage(ValidationError, "quantidade ou horas"):
            self.create_execution(executed_quantity=Decimal("10.0001"), executed_value=Decimal("1.00"))
        with self.assertRaisesMessage(ValidationError, "valor total"):
            self.create_execution(executed_quantity=Decimal("1.0000"), executed_value=Decimal("3000.01"))

    def test_execution_cannot_overspend_item_across_multiple_orders(self):
        self.create_execution(
            executed_quantity=Decimal("40.0000"), executed_value=Decimal("10000.00")
        )
        second_order = create_work_order(
            contract_id=self.contract.pk, actor=self.owner,
            **work_order_data(
                self.item, number="OS-RASCUNHO-2", hours=Decimal("70.0000"),
                status=WorkOrderStatus.DRAFT,
            ),
        )
        with self.assertRaisesMessage(ValidationError, "saldo quantitativo do item"):
            create_work_order_execution(
                work_order_id=second_order.pk, actor=self.owner,
                **execution_data(
                    executed_quantity=Decimal("61.0000"), executed_value=Decimal("15000.00")
                ),
            )

    def test_execution_respects_each_contract_year_limit(self):
        self.contract.validity_end = date(2028, 1, 9)
        self.contract.save()
        self.item.contracted_quantity = Decimal("120.0000")
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        self.create_execution(
            executed_quantity=Decimal("40.0000"),
            executed_value=Decimal("10000.00"),
            execution_date=date(2026, 9, 29),
        )
        second_order = create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(
                self.item,
                number="OS-EXEC-ANUAL-2",
                hours=Decimal("40.0000"),
                opening_date=date(2026, 10, 1),
                status=WorkOrderStatus.DRAFT,
            ),
        )
        with self.assertRaisesMessage(ValidationError, "ano contratual 1"):
            create_work_order_execution(
                work_order_id=second_order.pk,
                actor=self.owner,
                **execution_data(
                    executed_quantity=Decimal("20.0001"),
                    executed_value=Decimal("5000.00"),
                    execution_date=date(2026, 10, 2),
                ),
            )
        third_order = create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(
                self.item,
                number="OS-EXEC-ANUAL-3",
                hours=Decimal("40.0000"),
                opening_date=date(2027, 2, 1),
                status=WorkOrderStatus.DRAFT,
            ),
        )
        execution = create_work_order_execution(
            work_order_id=third_order.pk,
            actor=self.owner,
            **execution_data(
                executed_quantity=Decimal("40.0000"),
                executed_value=Decimal("10000.00"),
                execution_date=date(2027, 2, 2),
            ),
        )
        self.assertEqual(execution.executed_quantity, Decimal("40.0000"))

    def test_order_cannot_be_reduced_below_execution(self):
        self.create_execution()
        with self.assertRaisesMessage(ValidationError, "quantidade já executada"):
            update_work_order(
                work_order_id=self.order.pk, actor=self.owner,
                **work_order_data(
                    self.item, number=self.order.number, hours=Decimal("9.0000"),
                    status=WorkOrderStatus.IN_PROGRESS,
                ),
            )

    def test_update_is_audited_and_record_is_not_deleted(self):
        execution = self.create_execution()
        updated = update_work_order_execution(
            execution_id=execution.pk, actor=self.owner,
            **execution_data(executed_quantity=Decimal("12.0000"), notes="Medição corrigida"),
        )
        self.assertEqual(updated.executed_quantity, Decimal("12.0000"))
        event = updated.events.first()
        self.assertEqual(event.event_type, WorkOrderExecutionEvent.EventType.UPDATED)
        self.assertEqual(event.details["anterior"]["quantidade_executada"], "10.0000")
        self.assertTrue(WorkOrderExecution.objects.filter(pk=execution.pk).exists())

    def test_item_and_contract_positions_use_execution_evidence(self):
        execution = self.create_execution()
        item_position = item_financial_position(self.item)
        contract_position = contract_financial_position(self.contract)
        self.assertEqual(item_position.used_quantity.value, Decimal("10.0000"))
        self.assertEqual(item_position.used_value.value, Decimal("2500.00"))
        self.assertEqual(item_position.used_value.evidence[0].source_id, str(execution.pk))
        self.assertEqual(contract_position.executed_value.value, Decimal("2500.00"))
        self.assertNotEqual(contract_position.committed_value.value, contract_position.executed_value.value)

    def test_canceled_order_rejects_new_execution_but_preserves_existing(self):
        execution = self.create_execution()
        self.order.status = WorkOrderStatus.CANCELED
        self.order.cancellation_reason = "Cancelamento posterior à execução"
        self.order.canceled_by = self.owner
        from django.utils import timezone
        self.order.canceled_at = timezone.now()
        self.order.save()
        with self.assertRaisesMessage(ValidationError, "OS cancelada"):
            self.create_execution(executed_quantity=Decimal("1.0000"), executed_value=Decimal("1.00"))
        self.assertTrue(WorkOrderExecution.objects.filter(pk=execution.pk).exists())

    def test_cross_contract_access_is_hidden_and_read_only_admin_cannot_write(self):
        execution = self.create_execution()
        with self.assertRaises(WorkOrderExecution.DoesNotExist):
            update_work_order_execution(
                execution_id=execution.pk, actor=self.other, **execution_data()
            )
        self.client.force_login(self.other)
        url = reverse("contracts:execution_update", args=[self.contract.pk, self.order.pk, execution.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_workorderexecution_add")).status_code,
            403,
        )

    def test_web_form_localizes_values_and_exposes_execution_separately(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:execution_create", args=[self.contract.pk, self.order.pk]),
            {
                "executed_quantity": "10,5000", "executed_value": "2.625,00",
                "execution_date": "2026-09-29", "competence": "09/2026",
                "notes": "Execução parcial", "evidence_reference": "Relatório 2",
            },
        )
        self.assertRedirects(
            response, reverse("contracts:work_order_detail", args=[self.contract.pk, self.order.pk])
        )
        execution = WorkOrderExecution.objects.get()
        self.assertEqual(execution.executed_value, Decimal("2625.00"))
        detail = self.client.get(reverse("contracts:work_order_detail", args=[self.contract.pk, self.order.pk]))
        self.assertContains(detail, "Execução, faturamento e pagamento são eventos distintos")
        self.assertContains(detail, "2.625,00")

    def test_no_delete_route_and_permissions_are_least_privilege(self):
        self.assertTrue(self.owner.has_perm("contracts.add_workorderexecution"))
        self.assertTrue(self.owner.has_perm("contracts.change_workorderexecution"))
        self.assertTrue(self.admin.has_perm("contracts.view_workorderexecution"))
        self.assertFalse(self.admin.has_perm("contracts.add_workorderexecution"))
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("execution_delete", route_names)

    def test_unauthenticated_create_is_forbidden(self):
        response = self.client.get(
            reverse("contracts:execution_create", args=[self.contract.pk, self.order.pk])
        )
        self.assertEqual(response.status_code, 403)
        anonymous = type("Anonymous", (), {"is_authenticated": False, "has_perm": lambda *args: False})()
        with self.assertRaises(PermissionDenied):
            create_work_order_execution(
                work_order_id=self.order.pk, actor=anonymous, **execution_data()
            )
