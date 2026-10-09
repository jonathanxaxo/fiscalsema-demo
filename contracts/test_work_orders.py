from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import (
    ContractItemUnit,
    ContractItem,
    WorkOrder,
    WorkOrderEvent,
    WorkOrderStatus,
)
from .services import (
    cancel_work_order,
    contract_financial_position,
    create_contract,
    create_contract_item,
    create_work_order,
    update_contract_item,
    update_work_order,
)
from .test_items import item_data
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


def work_order_data(item, **overrides):
    data = {
        "number": "OS-001/2026",
        "item": item,
        "description": "Execução dos serviços contratados",
        "quantity": None,
        "hours": Decimal("40.0000"),
        "responsible": "Responsável confirmado",
        "opening_date": date(2026, 9, 28),
        "signature_date": None,
        "start_date": None,
        "deadline": date(2026, 10, 31),
        "completion_date": None,
        "status": WorkOrderStatus.DRAFT,
        "process_number": "PROCESSO-OS-001",
        "notes": "",
    }
    data.update(overrides)
    return data


class WorkOrderBase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização de OS")
        self.owner = User.objects.create_user(
            email="dono.os@example.local",
            full_name="Fiscal Responsável pela OS",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro.os@example.local",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.os@example.local",
            full_name="Administrador de OS",
            password=VALID_PASSWORD,
        )
        self.manager = User.objects.create_user(
            email="gestor.os@example.local",
            full_name="Gestor de OS",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(contracted_quantity=Decimal("100.0000"), unit_value=Decimal("250.00")),
        )
        self.client = Client()

    def create_work_order(self, **overrides):
        return create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(self.item, **overrides),
        )


class WorkOrderModelTests(WorkOrderBase):
    def test_hour_order_copies_item_value_and_calculates_exact_decimal_total(self):
        work_order = self.create_work_order(hours=Decimal("40.0000"))
        self.assertEqual(work_order.unit_value, Decimal("250.00"))
        self.assertEqual(work_order.unit_name, "Hora")
        self.assertEqual(work_order.total_value, Decimal("10000.00"))
        self.assertIsInstance(work_order.total_value, Decimal)

    def test_quantity_order_uses_quantity_and_rejects_wrong_measure(self):
        item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(
                number="2",
                unit=ContractItemUnit.UNIT,
                contracted_quantity=Decimal("10.0000"),
                unit_value=Decimal("100.00"),
            ),
        )
        order = create_work_order(
            contract_id=self.contract.pk,
            actor=self.owner,
            **work_order_data(
                item,
                number="OS-UNIT-1",
                quantity=Decimal("2.0000"),
                hours=None,
            ),
        )
        self.assertEqual(order.measure, Decimal("2.0000"))
        with self.assertRaisesMessage(ValidationError, "Somente item por hora"):
            create_work_order(
                contract_id=self.contract.pk,
                actor=self.owner,
                **work_order_data(
                    item,
                    number="OS-UNIT-2",
                    quantity=Decimal("2.0000"),
                    hours=Decimal("1.0000"),
                ),
            )

    def test_item_must_be_active_and_belong_to_contract(self):
        second_contract = create_contract(
            actor=self.owner,
            **contract_data(number="038/2026", process_number="PROCESSO-002"),
        )
        foreign_item = create_contract_item(
            contract_id=second_contract.pk,
            actor=self.owner,
            **item_data(number="OUTRO"),
        )
        with self.assertRaises(ContractItem.DoesNotExist):
            create_work_order(
                contract_id=self.contract.pk,
                actor=self.owner,
                **work_order_data(foreign_item),
            )
        self.item.is_active = False
        self.item.save()
        with self.assertRaises(ContractItem.DoesNotExist):
            self.create_work_order(number="OS-INATIVA")

    def test_number_does_not_receive_unproved_uniqueness(self):
        first = self.create_work_order(number="OS-ABC")
        second = self.create_work_order(number="OS-ABC")
        self.assertNotEqual(first.pk, second.pk)

    def test_reference_value_is_immutable_and_preserved_if_item_changes(self):
        order = self.create_work_order()
        self.item.unit_value = Decimal("300.00")
        self.item.unit = ContractItemUnit.UNIT
        self.item.save()
        order.description = "Edição sem alterar referência"
        order.save()
        order.item.refresh_from_db()
        self.assertEqual(order.unit_value, Decimal("250.00"))
        self.assertEqual(order.unit_name, "Hora")
        self.assertEqual(order.current_item_value_difference, Decimal("-50.00"))
        order.unit_value = Decimal("300.00")
        with self.assertRaisesMessage(ValidationError, "não pode ser alterado"):
            order.save()

    def test_financial_effect_is_explicit_and_unknown_is_not_guessed(self):
        order = self.create_work_order()
        self.assertFalse(order.financial_effect)
        order.status = WorkOrderStatus.OPEN
        self.assertIsNone(order.financial_effect)
        order.status = WorkOrderStatus.SUSPENDED
        self.assertIsNone(order.financial_effect)
        order.status = WorkOrderStatus.SIGNED
        self.assertTrue(order.financial_effect)
        order.status = WorkOrderStatus.CANCELED
        self.assertFalse(order.financial_effect)


class WorkOrderFinancialTests(WorkOrderBase):
    def test_annual_limit_is_independent_for_each_contract_year(self):
        self.contract.validity_start = date(2026, 7, 1)
        self.contract.validity_end = date(2028, 6, 30)
        self.contract.save()
        self.item.contracted_quantity = Decimal("120.0000")
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        self.create_work_order(
            number="OS-ANO-1",
            hours=Decimal("60.0000"),
            opening_date=date(2027, 6, 30),
            status=WorkOrderStatus.OPEN,
        )
        with self.assertRaisesMessage(ValidationError, "ano contratual 1"):
            self.create_work_order(
                number="OS-EXCESSO-ANO-1",
                hours=Decimal("0.0001"),
                opening_date=date(2027, 6, 30),
                status=WorkOrderStatus.OPEN,
            )
        second_year = self.create_work_order(
            number="OS-ANO-2",
            hours=Decimal("60.0000"),
            opening_date=date(2027, 7, 1),
            status=WorkOrderStatus.OPEN,
        )
        self.assertEqual(
            second_year.annual_period_context["contract"].label,
            "Ano contratual 2",
        )

    def test_draft_and_canceled_orders_do_not_consume_annual_limit(self):
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        self.create_work_order(
            number="OS-RASCUNHO-ANUAL",
            hours=Decimal("60.0000"),
            status=WorkOrderStatus.DRAFT,
        )
        created = self.create_work_order(
            number="OS-VALIDA-ANUAL",
            hours=Decimal("60.0000"),
            status=WorkOrderStatus.OPEN,
        )
        self.assertEqual(created.hours, Decimal("60.0000"))

    def test_annual_limit_change_is_blocked_after_work_order_history(self):
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        self.create_work_order(status=WorkOrderStatus.DRAFT)
        payload = item_data(
            number=self.item.number,
            contracted_quantity=self.item.contracted_quantity,
            unit_value=self.item.unit_value,
            annual_operational_limit=Decimal("50.0000"),
        )
        with self.assertRaisesMessage(ValidationError, "análise de impacto"):
            update_contract_item(item_id=self.item.pk, actor=self.owner, **payload)

    def test_non_draft_orders_cannot_exceed_item_or_contract_capacity(self):
        self.create_work_order(
            number="OS-001",
            hours=Decimal("60.0000"),
            status=WorkOrderStatus.OPEN,
        )
        with self.assertRaisesMessage(ValidationError, "saldo de horas"):
            self.create_work_order(
                number="OS-002",
                hours=Decimal("40.0001"),
                status=WorkOrderStatus.SIGNED,
            )
        expensive_item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(
                number="EXP",
                contracted_quantity=Decimal("2.0000"),
                unit_value=Decimal("60000.00"),
            ),
        )
        with self.assertRaisesMessage(ValidationError, "saldo de valor"):
            create_work_order(
                contract_id=self.contract.pk,
                actor=self.owner,
                **work_order_data(
                    expensive_item,
                    number="OS-EXP",
                    hours=Decimal("2.0000"),
                    status=WorkOrderStatus.IN_PROGRESS,
                ),
            )

    def test_contract_position_includes_only_confirmed_financial_statuses(self):
        signed = self.create_work_order(
            number="OS-SIGNED",
            hours=Decimal("20.0000"),
            status=WorkOrderStatus.SIGNED,
        )
        self.create_work_order(
            number="OS-OPEN",
            hours=Decimal("10.0000"),
            status=WorkOrderStatus.OPEN,
        )
        position = contract_financial_position(self.contract)
        self.assertEqual(position.committed_value.value, signed.total_value)
        self.assertEqual(
            position.contract_balance.value,
            self.contract.current_value - signed.total_value,
        )
        self.assertEqual(position.committed_value.evidence[0].source_type, "ORDEM_SERVICO")


class WorkOrderLifecycleAndAccessTests(WorkOrderBase):
    def test_creation_update_and_cancel_are_audited_and_cancel_is_read_only(self):
        order = self.create_work_order()
        self.assertTrue(
            WorkOrderEvent.objects.filter(
                work_order=order, event_type=WorkOrderEvent.EventType.CREATED
            ).exists()
        )
        update_work_order(
            work_order_id=order.pk,
            actor=self.owner,
            **work_order_data(
                self.item,
                number=order.number,
                description="Descrição atualizada",
                status=WorkOrderStatus.SIGNED,
            ),
        )
        canceled = cancel_work_order(
            work_order_id=order.pk,
            actor=self.owner,
            reason="  Cancelamento   formalmente justificado  ",
        )
        self.assertEqual(canceled.status, WorkOrderStatus.CANCELED)
        self.assertEqual(canceled.cancellation_reason, "Cancelamento formalmente justificado")
        self.assertEqual(canceled.canceled_by, self.owner)
        self.assertIsNotNone(canceled.canceled_at)
        event = WorkOrderEvent.objects.get(
            work_order=order, event_type=WorkOrderEvent.EventType.CANCELED
        )
        self.assertEqual(event.details["anterior"]["status"], WorkOrderStatus.SIGNED)
        self.assertEqual(event.details["atual"]["status"], WorkOrderStatus.CANCELED)
        with self.assertRaisesMessage(ValidationError, "somente leitura"):
            update_work_order(
                work_order_id=order.pk,
                actor=self.owner,
                **work_order_data(self.item),
            )

    def test_cancel_requires_reason_and_never_deletes_order(self):
        order = self.create_work_order()
        with self.assertRaisesMessage(ValidationError, "motivo"):
            cancel_work_order(work_order_id=order.pk, actor=self.owner, reason="  ")
        self.assertTrue(WorkOrder.objects.filter(pk=order.pk).exists())

    def test_other_fiscal_cannot_discover_or_change_order(self):
        order = self.create_work_order()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:work_order_list", args=[self.contract.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:work_order_detail", args=[self.contract.pk, order.pk])
            ).status_code,
            404,
        )
        with self.assertRaises(WorkOrder.DoesNotExist):
            cancel_work_order(
                work_order_id=order.pk,
                actor=self.other,
                reason="Tentativa indevida",
            )

    def test_owner_uses_localized_form_and_administrator_is_read_only(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:work_order_create", args=[self.contract.pk]),
            {
                "number": "OS-WEB",
                "item": self.item.pk,
                "description": "OS criada pelo formulário",
                "quantity": "",
                "hours": "1,5000",
                "responsible": "Responsável",
                "opening_date": "2026-09-28",
                "signature_date": "",
                "start_date": "",
                "deadline": "2026-10-31",
                "completion_date": "",
                "status": WorkOrderStatus.DRAFT,
                "process_number": "PROCESSO-WEB",
                "notes": "",
            },
        )
        created = WorkOrder.objects.get(number="OS-WEB")
        self.assertRedirects(
            response,
            reverse("contracts:work_order_detail", args=[self.contract.pk, created.pk]),
        )
        self.assertEqual(created.hours, Decimal("1.5000"))
        self.client.force_login(self.admin)
        detail = self.client.get(
            reverse("contracts:work_order_detail", args=[self.contract.pk, created.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(detail, "Editar OS")
        self.assertNotContains(detail, "Cancelar OS")
        self.assertEqual(
            self.client.get(reverse("contracts:work_order_create", args=[self.contract.pk])).status_code,
            403,
        )

    def test_permissions_admin_read_only_and_no_delete_route(self):
        self.assertTrue(self.owner.has_perm("contracts.add_workorder"))
        self.assertTrue(self.owner.has_perm("contracts.change_workorder"))
        self.assertTrue(self.manager.has_perm("contracts.view_workorder"))
        self.assertFalse(self.manager.has_perm("contracts.add_workorder"))
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_workorder_add")).status_code,
            403,
        )
        route_names = [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns]
        self.assertNotIn("work_order_delete", route_names)
