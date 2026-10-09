from datetime import date
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from .models import ContractItemEvent, WorkOrderAllocationStatus, WorkOrderStatus
from .services import (
    create_budget_commitment,
    create_contract,
    create_contract_item,
    create_invoice,
    create_work_order_allocation,
    share_contract_read_only,
)
from .test_commitments import commitment_data
from .test_invoices import invoice_data
from .test_items import item_data
from .test_work_orders import WorkOrderBase
from .tests import contract_data


class TableModeTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS
        )
        self.commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )
        self.allocation = create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            commitment=self.commitment,
            amount=Decimal("6000.00"),
            allocation_date=date(2026, 9, 29),
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        self.invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                item=self.item,
                allocation=self.allocation,
                gross_value=Decimal("6000.00"),
            ),
        )
        self.client = Client()

    def url(self, table_type="items", **params):
        query = {"tipo": table_type, **params}
        return reverse("contracts:table_mode", args=[self.contract.pk]) + "?" + "&".join(
            f"{key}={value}" for key, value in query.items()
        )

    def test_all_five_tables_render_scoped_operational_data(self):
        self.client.force_login(self.owner)
        expectations = {
            "items": self.item.number,
            "commitments": self.commitment.number,
            "work_orders": self.order.number,
            "allocations": self.commitment.number,
            "invoices": self.invoice.number,
        }
        for table_type, text in expectations.items():
            with self.subTest(table_type=table_type):
                response = self.client.get(self.url(table_type))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, text)
                self.assertContains(response, "data-table-mode")

    def test_search_filters_on_server(self):
        second = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(number="ITEM-PESQUISADO", description="Objeto singular"),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url("items", q="singular"))
        self.assertContains(response, second.number)
        self.assertNotContains(response, self.item.description)

    def test_ordering_uses_only_whitelisted_fields(self):
        first_ordered = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(number="AAA-ITEM"),
        )
        second_ordered = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(number="ZZZ-ITEM"),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url("items", ordenar="-number"))
        content = response.content.decode()
        self.assertLess(content.index(second_ordered.number), content.index(first_ordered.number))
        invalid = self.client.get(self.url("items", ordenar="created_by__password"))
        self.assertEqual(invalid.context["selected_ordering"], "number")

    def test_pagination_limits_each_page_to_twenty_five(self):
        for index in range(25):
            create_contract_item(
                contract_id=self.contract.pk,
                actor=self.owner,
                **item_data(number=f"ITEM-{index:03d}"),
            )
        self.client.force_login(self.owner)
        first = self.client.get(self.url("items"))
        second = self.client.get(self.url("items", pagina=2))
        self.assertEqual(len(first.context["rows"]), 25)
        self.assertEqual(len(second.context["rows"]), 1)
        self.assertContains(first, "Página 1 de 2")

    def test_read_only_user_can_use_table_without_edit_actions(self):
        share_contract_read_only(
            contract_id=self.contract.pk,
            actor=self.owner,
            email=self.other.email,
        )
        self.client.force_login(self.other)
        response = self.client.get(self.url("items"))
        self.assertContains(response, "Somente leitura")
        self.assertNotContains(
            response, reverse("contracts:item_update", args=[self.contract.pk, self.item.pk])
        )
        self.assertContains(
            response, reverse("contracts:item_detail", args=[self.contract.pk, self.item.pk])
        )

    def test_foreign_contract_and_anonymous_access_are_blocked(self):
        self.assertEqual(
            self.client.get(reverse("contracts:table_mode", args=[self.contract.pk])).status_code,
            302,
        )
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:table_mode", args=[self.contract.pk])).status_code,
            404,
        )

    def test_records_from_another_contract_never_leak(self):
        other_contract = create_contract(
            actor=self.owner,
            **contract_data(number="099/2026", process_number="PROCESSO-099"),
        )
        foreign = create_contract_item(
            contract_id=other_contract.pk,
            actor=self.owner,
            **item_data(number="ITEM-SEGREDO"),
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url("items", q="ITEM"))
        self.assertNotContains(response, foreign.number)

    def test_calculated_fields_are_locked_and_identified(self):
        self.client.force_login(self.owner)
        items = self.client.get(self.url("items"))
        commitments = self.client.get(self.url("commitments"))
        self.assertContains(items, "Total calculado")
        self.assertContains(items, "class=\"calculated\"")
        self.assertContains(commitments, "Comprometido")
        self.assertContains(commitments, "Saldo")

    def test_quick_edit_reuses_validated_forms(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url("invoices"))
        self.assertContains(
            response,
            reverse(
                "contracts:invoice_update",
                args=[self.contract.pk, self.order.pk, self.invoice.pk],
            ),
        )
        self.assertContains(response, ">Editar</a>", html=False)

    def test_keyboard_copy_paste_and_resize_assets_are_loaded(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url("items"))
        self.assertContains(response, "contracts/table_mode.js")
        self.assertContains(response, "contracts/table_mode.css")
        self.assertContains(response, "Tab, Shift+Tab e setas")
        self.assertContains(response, "Ctrl+C")
        self.assertContains(response, "colunas")

    def test_invalid_table_type_falls_back_to_items(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url("segredos"))
        self.assertEqual(response.context["selected_type"], "items")
        self.assertContains(response, self.item.number)

    def test_table_mode_is_read_only_transport_and_post_is_rejected(self):
        self.client.force_login(self.owner)
        event_count = ContractItemEvent.objects.count()
        response = self.client.post(
            reverse("contracts:table_mode", args=[self.contract.pk]),
            {"number": "ALTERACAO-INDEVIDA"},
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(ContractItemEvent.objects.count(), event_count)
