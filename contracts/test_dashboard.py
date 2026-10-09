from datetime import date
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from accounts.models import AccountStatus, RegistrationRequest

from .dashboard import LOW_BALANCE_PERCENT, build_contract_dashboard
from .models import WorkOrderAllocationStatus, WorkOrderStatus
from .services import (
    cancel_work_order,
    create_budget_commitment,
    create_contract,
    create_contract_item,
    create_invoice,
    create_payment,
    create_work_order_allocation,
    create_work_order_execution,
    create_work_order,
)
from .test_commitments import commitment_data
from .test_executions import execution_data
from .test_invoices import invoice_data
from .test_items import item_data
from .test_payments import payment_data
from .test_work_orders import WorkOrderBase, work_order_data
from .tests import contract_data


class DashboardTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(
            hours=Decimal("40.0000"),
            status=WorkOrderStatus.IN_PROGRESS,
            deadline=date(2026, 10, 10),
        )
        self.client = Client()

    def test_dashboard_reuses_financial_layer_and_exposes_seven_totals(self):
        commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("12000.00")),
        )
        create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            commitment=commitment,
            amount=Decimal("10000.00"),
            allocation_date=date(2026, 9, 30),
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        create_work_order_execution(
            work_order_id=self.order.pk,
            actor=self.owner,
            **execution_data(
                executed_quantity=Decimal("20.0000"),
                executed_value=Decimal("5000.00"),
            ),
        )
        invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                gross_value=Decimal("4000.00"),
                accepted_value=Decimal("4000.00"),
            ),
        )
        create_payment(
            invoice_id=invoice.pk,
            actor=self.owner,
            **payment_data(amount=Decimal("2500.00")),
        )

        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        position = dashboard.financial_position
        self.assertEqual(self.contract.current_value, Decimal("100000.00"))
        self.assertEqual(position.total_committed_budget.value, Decimal("12000.00"))
        self.assertEqual(position.committed_value.value, Decimal("10000.00"))
        self.assertEqual(position.executed_value.value, Decimal("5000.00"))
        self.assertEqual(position.invoiced_gross_value.value, Decimal("4000.00"))
        self.assertEqual(position.paid_value.value, Decimal("2500.00"))
        self.assertEqual(position.contract_balance.value, Decimal("90000.00"))

    def test_deadlines_are_deterministic_without_invented_near_window(self):
        self.order.deadline = date(2026, 9, 29)
        self.order.save()
        future = self.create_work_order(
            number="OS-FUTURA",
            hours=Decimal("20.0000"),
            status=WorkOrderStatus.OPEN,
            deadline=date(2027, 6, 1),
        )
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        self.assertEqual(dashboard.overdue_work_orders, (self.order,))
        self.assertEqual(dashboard.upcoming_work_orders, (future,))

    def test_management_summary_reuses_item_and_commitment_calculation_layers(self):
        commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("12000.00")),
        )
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))

        self.assertEqual(dashboard.item_positions[0].item, self.item)
        self.assertEqual(
            dashboard.item_positions[0].position.total_value.value,
            self.item.total_value,
        )
        self.assertEqual(dashboard.item_total, self.item.total_value)
        self.assertEqual(dashboard.active_item_count, 1)
        self.assertEqual(dashboard.inactive_item_count, 0)
        self.assertEqual(dashboard.commitment_positions[0].commitment, commitment)
        self.assertEqual(
            dashboard.commitment_positions[0].position.available_balance.value,
            Decimal("12000.00"),
        )

    def test_operational_pending_items_are_derived_without_changing_balances(self):
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        self.assertEqual(dashboard.work_orders_without_allocation, (self.order,))

        self.order.status = WorkOrderStatus.COMPLETED
        self.order.completion_date = date(2026, 9, 30)
        self.order.save()
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        self.assertEqual(dashboard.completed_work_orders_without_invoice, (self.order,))
        self.assertEqual(
            {entry.value: entry.count for entry in dashboard.work_order_statuses},
            {WorkOrderStatus.COMPLETED: 1},
        )

    def test_financial_calendar_uses_documented_invoice_plus_ten_days_rule(self):
        invoice = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                issue_date=date(2026, 9, 1),
                gross_value=Decimal("2000.00"),
                accepted_value=Decimal("2000.00"),
            ),
        )
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        deadline = dashboard.invoice_financial_deadlines[0]
        self.assertEqual(deadline.invoice, invoice)
        self.assertEqual(deadline.deadline, date(2026, 9, 11))
        self.assertTrue(deadline.is_overdue)
        self.assertEqual(dashboard.finance_submission_days, 10)
        self.assertEqual(dashboard.invoice_count, 1)
        self.assertEqual(dashboard.payment_count, 0)

    def test_pending_and_duplicate_invoices_are_separated(self):
        pending = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                number="NF-PENDENTE",
                gross_value=Decimal("2000.00"),
                accepted_value=Decimal("2000.00"),
            ),
        )
        first_duplicate = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                number="NF-DUPLICADA",
                gross_value=Decimal("1000.00"),
                accepted_value=Decimal("1000.00"),
            ),
        )
        second_duplicate = create_invoice(
            work_order_id=self.order.pk,
            actor=self.owner,
            **invoice_data(
                self.contract,
                number="NF-DUPLICADA",
                gross_value=Decimal("1000.00"),
                accepted_value=Decimal("1000.00"),
            ),
        )
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        self.assertIn(pending.pk, [entry.invoice.pk for entry in dashboard.pending_invoices])
        duplicate_ids = [entry.invoice.pk for entry in dashboard.divergent_invoices]
        self.assertIn(first_duplicate.pk, duplicate_ids)
        self.assertIn(second_duplicate.pk, duplicate_ids)

    def test_low_commitment_contract_and_hour_balances_use_strict_twenty_percent(self):
        contract = create_contract(
            actor=self.owner,
            **contract_data(
                number="SALDO-BAIXO/2026",
                process_number="PROCESSO-SALDO-BAIXO",
                original_value=Decimal("25000.00"),
            ),
        )
        item = create_contract_item(
            contract_id=contract.pk,
            actor=self.owner,
            **item_data(
                number="SALDO-1",
                contracted_quantity=Decimal("100.0000"),
                unit_value=Decimal("250.00"),
            ),
        )
        order = create_work_order(
            contract_id=contract.pk,
            actor=self.owner,
            **work_order_data(
                item,
                number="OS-SALDO-1",
                hours=Decimal("40.0000"),
                status=WorkOrderStatus.IN_PROGRESS,
            ),
        )
        commitment = create_budget_commitment(
            contract_id=contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )
        create_work_order_allocation(
            work_order_id=order.pk,
            actor=self.owner,
            commitment=commitment,
            amount=Decimal("8500.00"),
            allocation_date=date(2026, 9, 30),
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        second_order = create_work_order(
            contract_id=contract.pk,
            actor=self.owner,
            **work_order_data(
                item,
                number="OS-HORAS-2",
                hours=Decimal("50.0000"),
                status=WorkOrderStatus.IN_PROGRESS,
            ),
        )
        create_work_order_execution(
            work_order_id=order.pk,
            actor=self.owner,
            **execution_data(
                executed_quantity=Decimal("40.0000"),
                executed_value=Decimal("10000.00"),
            ),
        )
        create_work_order_execution(
            work_order_id=second_order.pk,
            actor=self.owner,
            **execution_data(
                executed_quantity=Decimal("45.0000"),
                executed_value=Decimal("11250.00"),
            ),
        )
        dashboard = build_contract_dashboard(contract, today=date(2026, 9, 30))
        self.assertEqual(LOW_BALANCE_PERCENT, Decimal("20.00"))
        self.assertEqual(dashboard.low_commitments[0].percentage, Decimal("15.00"))
        self.assertEqual(dashboard.low_hour_items[0].percentage, Decimal("15.00"))
        self.assertTrue(dashboard.contract_balance_is_low)
        self.assertEqual(dashboard.contract_balance_percentage, Decimal("10.00"))

    def test_exactly_twenty_percent_is_not_reported_as_below_twenty(self):
        commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("10000.00")),
        )
        create_work_order_allocation(
            work_order_id=self.order.pk,
            actor=self.owner,
            commitment=commitment,
            amount=Decimal("8000.00"),
            allocation_date=date(2026, 9, 30),
            status=WorkOrderAllocationStatus.ACTIVE,
        )
        dashboard = build_contract_dashboard(self.contract, today=date(2026, 9, 30))
        self.assertEqual(dashboard.low_commitments, ())

    def test_dashboard_keeps_civil_closing_and_contract_year_separate(self):
        self.contract.validity_start = date(2026, 7, 1)
        self.contract.validity_end = date(2028, 6, 30)
        self.contract.save()
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        dashboard = build_contract_dashboard(
            self.contract, today=date(2027, 8, 10)
        )
        self.assertEqual(dashboard.closing_rule.split(" — ")[0], "ANO CIVIL")
        self.assertEqual(len(dashboard.calendar_periods), 3)
        self.assertEqual(len(dashboard.contract_years), 2)
        self.assertEqual(
            dashboard.current_calendar_period.label, "Fechamento 2027"
        )
        self.assertEqual(
            dashboard.current_contract_year.label, "Ano contratual 2"
        )
        self.assertEqual(len(dashboard.annual_item_limits), 2)

    def test_annual_summaries_do_not_count_canceled_work_orders(self):
        cancel_work_order(
            work_order_id=self.order.pk,
            actor=self.owner,
            reason="Contratação extinta para validar o resumo anual.",
        )

        dashboard = build_contract_dashboard(
            self.contract, today=date(2026, 9, 30)
        )

        civil = dashboard.calendar_periods[0]
        contractual = dashboard.contract_years[0]
        self.assertEqual(civil.work_order_count, 0)
        self.assertEqual(civil.work_order_value, Decimal("0.00"))
        self.assertEqual(contractual.work_order_count, 0)
        self.assertEqual(contractual.work_order_value, Decimal("0.00"))

    def test_home_selects_one_authorized_contract_and_never_mixes_contexts(self):
        second = type(self.contract).objects.create(
            **contract_data(number="038/2026", process_number="PROCESSO-038"),
            contracting_organization=self.organization,
            responsible_fiscal=self.owner,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"), {"contract": second.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_contract"], second)
        self.assertEqual(response.context["dashboard"].contract, second)
        self.assertContains(response, "Contrato 038/2026")

    def test_other_fiscal_cannot_select_contract_outside_scope(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("home"), {"contract": self.contract.pk})
        self.assertEqual(response.status_code, 404)

    def test_invalid_contract_selector_is_rejected_without_server_error(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"), {"contract": "nao-numerico"})
        self.assertEqual(response.status_code, 404)

    def test_home_renders_cards_drill_down_and_empty_operational_state(self):
        empty_contract = type(self.contract).objects.create(
            **contract_data(number="039/2026", process_number="PROCESSO-039"),
            contracting_organization=self.organization,
            responsible_fiscal=self.owner,
        )
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"), {"contract": empty_contract.pk})
        self.assertContains(response, "Como está meu contrato?")
        self.assertContains(response, "Empenhado ativo")
        self.assertContains(response, "Pago")
        self.assertContains(response, "Módulos de fiscalização")
        self.assertContains(response, "Consumo e saldo por item")
        self.assertContains(response, "Posição dos empenhos")
        self.assertContains(response, "Calendário financeiro")
        self.assertContains(response, "não possui movimentação operacional")
        self.assertContains(response, "Não foi presumida uma janela")
        self.assertContains(response, reverse("contracts:detail", args=[empty_contract.pk]))

    def test_dashboard_explains_and_collapses_annual_information(self):
        self.contract.validity_start = date(2026, 7, 23)
        self.contract.validity_end = date(2028, 7, 22)
        self.contract.save()
        self.item.annual_operational_limit = Decimal("60.0000")
        self.item.save()
        self.client.force_login(self.owner)

        response = self.client.get(reverse("contracts:dashboard", args=[self.contract.pk]))

        self.assertContains(response, "Ano civil")
        self.assertContains(response, "Ano contratual")
        self.assertContains(response, "Saldo para novas OS")
        self.assertContains(response, "Reservado em OS")
        self.assertContains(response, "Item 1")
        self.assertContains(response, "23/07/2026 a 22/07/2027")
        self.assertContains(response, "Fechamentos por ano")
        self.assertNotContains(response, "Fechamentos por ano civil")
        self.assertContains(response, 'class="dashboard-disclosure"', count=3)
        self.assertNotContains(response, 'class="dashboard-disclosure" open')

    def test_user_without_contract_sees_safe_empty_state(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum contrato disponível")
        self.assertIsNone(response.context["dashboard"])

    def test_administrator_sees_pending_registration_but_no_operational_create_link(self):
        pending = type(self.owner).objects.create_user(
            email="pendente.dashboard@example.local",
            full_name="Fiscal Pendente Dashboard",
            password="SenhaMuitoForte!2026",
            status=AccountStatus.PENDING_APPROVAL,
        )
        RegistrationRequest.objects.create(user=pending)
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"), {"contract": self.contract.pk})
        self.assertEqual(response.context["pending_registration_count"], 1)
        self.assertContains(response, "Solicitações de cadastro (1)")
        self.assertNotContains(
            response,
            reverse("contracts:item_create", args=[self.contract.pk]),
        )
