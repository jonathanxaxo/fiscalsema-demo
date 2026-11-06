from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus
from organizations.models import Organization

from .calculations import (
    CalculationEvidence,
    NegativeBalanceError,
    calculate_commitment_financial_position,
    calculate_contract_financial_position,
    calculate_item_financial_position,
)
from .models import CommitmentMovement, ContractItemUnit
from .services import (
    commitment_financial_position,
    contract_financial_position,
    create_budget_commitment,
    create_commitment_movement,
    create_contract,
    create_contract_item,
    item_financial_position,
    update_budget_commitment,
)
from .test_commitments import commitment_data, movement_data
from .test_items import item_data
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


def evidence(identifier, value, description="Registro de origem"):
    return CalculationEvidence(
        source_type="TESTE",
        source_id=str(identifier),
        description=description,
        value=Decimal(value),
    )


class FinancialEngineUnitTests(TestCase):
    def test_item_position_is_exact_and_exposes_origin_of_each_total(self):
        position = calculate_item_financial_position(
            item_id=10,
            contracted_quantity=Decimal("100.0000"),
            unit_value=Decimal("250.00"),
            used_quantity_evidence=(evidence("OS-1", "40.0000"),),
            used_value_evidence=(evidence("EXEC-1", "10000.00"),),
        )
        self.assertEqual(position.total_value.value, Decimal("25000.00"))
        self.assertEqual(position.used_quantity.value, Decimal("40.0000"))
        self.assertEqual(position.quantity_balance.value, Decimal("60.0000"))
        self.assertEqual(position.used_value.value, Decimal("10000.00"))
        self.assertEqual(position.financial_balance.value, Decimal("15000.00"))
        self.assertEqual(position.quantity_balance.evidence[-1].operation, "SUBTRACT")
        self.assertEqual(position.financial_balance.evidence[-1].source_id, "EXEC-1")

    def test_item_position_blocks_quantity_or_value_overspending(self):
        with self.assertRaises(NegativeBalanceError):
            calculate_item_financial_position(
                item_id=1,
                contracted_quantity=Decimal("10.0000"),
                unit_value=Decimal("2.00"),
                used_quantity_evidence=(evidence("OS-1", "10.0001"),),
            )
        with self.assertRaises(NegativeBalanceError):
            calculate_item_financial_position(
                item_id=1,
                contracted_quantity=Decimal("10.0000"),
                unit_value=Decimal("2.00"),
                used_value_evidence=(evidence("EXEC-1", "20.01"),),
            )

    def test_commitment_position_separates_current_committed_and_available(self):
        position = calculate_commitment_financial_position(
            commitment_id=20,
            initial_value=Decimal("100000.00"),
            reinforcement_evidence=(evidence("REF-1", "20000.00"),),
            cancellation_evidence=(evidence("ANU-1", "5000.00"),),
            committed_evidence=(evidence("RATEIO-1", "60000.00"),),
        )
        self.assertEqual(position.current_value.value, Decimal("115000.00"))
        self.assertEqual(position.committed_value.value, Decimal("60000.00"))
        self.assertEqual(position.available_balance.value, Decimal("55000.00"))
        operations = [entry.operation for entry in position.available_balance.evidence]
        self.assertEqual(operations, ["BASE", "ADD", "SUBTRACT", "SUBTRACT"])

    def test_commitment_and_contract_positions_block_negative_balances(self):
        with self.assertRaises(NegativeBalanceError):
            calculate_commitment_financial_position(
                commitment_id=1,
                initial_value=Decimal("100.00"),
                committed_evidence=(evidence("RATEIO", "100.01"),),
            )
        with self.assertRaises(NegativeBalanceError):
            calculate_contract_financial_position(
                contract_id=1,
                current_value=Decimal("100.00"),
                committed_evidence=(evidence("OS", "100.01"),),
            )

    def test_contract_position_does_not_mix_committed_budget_with_os_commitment(self):
        position = calculate_contract_financial_position(
            contract_id=30,
            current_value=Decimal("200000.00"),
            commitment_evidence=(
                evidence("EMP-1", "100000.00"),
                evidence("EMP-2", "50000.00"),
            ),
            committed_evidence=(evidence("OS-1", "60000.00"),),
        )
        self.assertEqual(position.total_committed_budget.value, Decimal("150000.00"))
        self.assertEqual(position.committed_value.value, Decimal("60000.00"))
        self.assertEqual(position.contract_balance.value, Decimal("140000.00"))

    def test_float_and_unidentified_or_negative_evidence_are_rejected(self):
        with self.assertRaises(TypeError):
            calculate_contract_financial_position(contract_id=1, current_value=100.0)
        with self.assertRaises(ValueError):
            CalculationEvidence("", "1", "Sem origem", Decimal("1.00"))
        with self.assertRaises(ValueError):
            evidence("NEGATIVO", "-0.01")


class FinancialEngineIntegrationTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização do Motor")
        self.fiscal = User.objects.create_user(
            email="motor@example.local",
            full_name="Fiscal do Motor",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.contract = create_contract(
            actor=self.fiscal,
            **contract_data(original_value=Decimal("200000.00")),
        )
        self.item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            **item_data(
                unit=ContractItemUnit.HOUR,
                contracted_quantity=Decimal("100.0000"),
                unit_value=Decimal("250.00"),
            ),
        )
        self.active_commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            **commitment_data(initial_value=Decimal("100000.00")),
        )
        create_commitment_movement(
            commitment_id=self.active_commitment.pk,
            actor=self.fiscal,
            **movement_data(amount=Decimal("25000.00")),
        )
        inactive = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            **commitment_data(
                number="INATIVO",
                ped="PED-INATIVO",
                commitment_date=date(2026, 9, 27),
                initial_value=Decimal("50000.00"),
            ),
        )
        update_budget_commitment(
            commitment_id=inactive.pk,
            actor=self.fiscal,
            **commitment_data(
                number="INATIVO",
                ped="PED-INATIVO",
                commitment_date=date(2026, 9, 27),
                initial_value=Decimal("50000.00"),
                is_active=False,
            ),
        )

    def test_model_adapters_use_only_existing_sources_and_active_commitments(self):
        item_position = item_financial_position(self.item)
        commitment_position = commitment_financial_position(self.active_commitment)
        contract_position = contract_financial_position(self.contract)
        self.assertEqual(item_position.used_quantity.value, Decimal("0"))
        self.assertEqual(item_position.quantity_balance.value, Decimal("100.0000"))
        self.assertEqual(commitment_position.current_value.value, Decimal("125000.00"))
        self.assertEqual(commitment_position.committed_value.value, Decimal("0"))
        self.assertEqual(commitment_position.available_balance.value, Decimal("125000.00"))
        self.assertEqual(contract_position.total_committed_budget.value, Decimal("125000.00"))
        self.assertEqual(contract_position.committed_value.value, Decimal("0"))
        self.assertEqual(contract_position.contract_balance.value, Decimal("200000.00"))
        self.assertEqual(
            contract_position.total_committed_budget.evidence[0].source_id,
            str(self.active_commitment.pk),
        )

    def test_authorized_detail_pages_show_derived_balances(self):
        client = Client()
        client.force_login(self.fiscal)
        contract_response = client.get(reverse("contracts:detail", args=[self.contract.pk]))
        item_response = client.get(
            reverse("contracts:item_detail", args=[self.contract.pk, self.item.pk])
        )
        commitment_response = client.get(
            reverse(
                "contracts:commitment_detail",
                args=[self.contract.pk, self.active_commitment.pk],
            )
        )
        self.assertContains(contract_response, "Total empenhado ativo")
        self.assertContains(contract_response, "125.000,00")
        self.assertContains(item_response, "Saldo quantitativo")
        self.assertContains(item_response, "100,00")
        self.assertContains(commitment_response, "Saldo disponível")
        self.assertContains(commitment_response, "125.000,00")
