"""Sprint 60: dados do Arise limitados ao perfil e valores escritos em reais."""

import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from accounts.models import AccountStatus, User, UserProfile
from contracts.models import (
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractItem,
    ContractItemUnit,
    WorkOrder,
    WorkOrderStatus,
)
from organizations.models import Organization

from .ferramentas import authorized_data, reais
from .prompt import MAX_DATA_CHARS

VALID_PASSWORD = "SenhaMuitoForte!2026"
CONTRACT_FINANCIAL_KEYS = (
    "financeiro",
    "erro_financeiro",
    "empenhado",
    "comprometido",
    "executado",
    "faturado",
    "pago",
    "saldo_contratual",
    "saldo_financeiro",
    "valor_utilizado",
    "valor_atual",
    "carteira_institucional",
    "itens",
    "regras_confirmadas",
    "pendencias_ativas",
)


class ReaisFormatTests(TestCase):
    def test_formats_backend_values_in_reais(self):
        self.assertEqual(reais(Decimal("22400")), "R$ 22.400,00")
        self.assertEqual(reais("224000.00"), "R$ 224.000,00")
        self.assertEqual(reais("0"), "R$ 0,00")
        self.assertEqual(reais("1234567.895"), "R$ 1.234.567,90")
        self.assertEqual(reais("-10.5"), "-R$ 10,50")

    def test_keeps_non_numeric_values_unchanged(self):
        self.assertEqual(reais(""), "")
        self.assertIsNone(reais(None))
        self.assertEqual(reais("não informado"), "não informado")


class AriseDataByProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Organização Demo Arise")
        cls.fiscal = cls._user("fiscal.arise@example.local", UserProfile.FISCAL_TITULAR)
        cls.auxiliary = cls._user(
            "auxiliar.arise@example.local", UserProfile.AUXILIARY_ADMINISTRATIVE
        )
        cls.administrative_manager = cls._user(
            "gestor.adm.arise@example.local", UserProfile.ADMINISTRATIVE_MANAGER
        )
        cls.contract_manager = cls._user(
            "gestor.contrato.arise@example.local", UserProfile.CONTRACT_MANAGER
        )
        cls.contract = cls._contract("DEMO-ARISE-01/2026")
        cls.archived_contract = cls._contract("DEMO-ARISE-ARQ/2026")
        Contract.objects.filter(pk=cls.archived_contract.pk).update(
            archived_at=timezone.now(),
            archived_by=cls.fiscal,
            archive_reason="Arquivado para teste fictício.",
        )
        ContractAccess.objects.create(
            contract=cls.contract,
            user=cls.contract_manager,
            access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE,
            granted_by=cls.fiscal,
        )
        item = ContractItem.objects.create(
            contract=cls.contract,
            number="1",
            description="Hora técnica fictícia",
            category="Serviço",
            unit=ContractItemUnit.HOUR,
            contracted_quantity=Decimal("500.0000"),
            unit_value=Decimal("250.00"),
            created_by=cls.fiscal,
        )
        WorkOrder.objects.create(
            contract=cls.contract,
            item=item,
            number="OS-ARISE-ATRASADA/2026",
            description="Execução exclusivamente fictícia",
            hours=Decimal("40.0000"),
            unit_value=item.unit_value,
            unit_name=item.unit_display,
            responsible="Responsável fictício",
            opening_date=date(2026, 1, 10),
            deadline=date(2026, 11, 18),
            status=WorkOrderStatus.OPEN,
            process_number="PROC-OS-ARISE",
            created_by=cls.fiscal,
        )

    @classmethod
    def _user(cls, email, profile):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0],
            password=VALID_PASSWORD,
            profile=profile,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )

    @classmethod
    def _contract(cls, number):
        return Contract.objects.create(
            number=number,
            process_number=f"PROC-{number}",
            object="Objeto exclusivamente fictício para teste",
            contracting_organization=cls.organization,
            supplier_name="Fornecedor Fictício Ltda.",
            supplier_tax_id="12345678000199",
            signature_date=date(2026, 1, 1),
            validity_start=date(2026, 1, 1),
            validity_end=date(2027, 12, 31),
            original_value=Decimal("100000.00"),
            responsible_fiscal=cls.fiscal,
        )

    def _keys(self, value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from self._keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from self._keys(child)

    @mock.patch(
        "core.profile_dashboards.timezone.localdate", return_value=date(2026, 11, 20)
    )
    def test_auxiliary_receives_open_orders_without_contract_finances(self, _today):
        for contract_id in (None, self.contract.pk):
            with self.subTest(contract_id=contract_id):
                text = authorized_data(
                    self.auxiliary, route="assistant:chat", contract_id=contract_id
                )
                payload = json.loads(text)
                keys = set(self._keys(payload))
                for forbidden in CONTRACT_FINANCIAL_KEYS:
                    self.assertNotIn(forbidden, keys)
                self.assertNotIn("R$ 100.000,00", text)
                self.assertNotIn("Fornecedor Fictício", text)
                self.assertIn(self.contract.number, text)
                self.assertNotIn(self.archived_contract.number, text)
                summary = payload["resumo_os_abertas"]
                self.assertEqual(summary["os_abertas"], 1)
                self.assertEqual(summary["os_em_atraso"], 1)
                self.assertEqual(summary["valor_das_os_abertas"], "R$ 10.000,00")
                order = payload["ordens_servico_abertas"][0]
                self.assertEqual(order["numero"], "OS-ARISE-ATRASADA/2026")
                self.assertTrue(order["em_atraso"])
                self.assertEqual(order["prazo"], "2026-11-18")
                self.assertEqual(order["valor_unitario_os"], "R$ 250,00")
                self.assertEqual(order["valor_da_os"], "R$ 10.000,00")
                self.assertLessEqual(len(text), MAX_DATA_CHARS)

    def test_auxiliary_cannot_reach_archived_or_missing_contract(self):
        for contract_id in (self.archived_contract.pk, 999999):
            with self.subTest(contract_id=contract_id):
                text = authorized_data(
                    self.auxiliary, route="assistant:chat", contract_id=contract_id
                )
                self.assertIn("Nenhum contrato autorizado", text)
                self.assertNotIn(self.archived_contract.number, text)

    def test_auxiliary_data_stays_valid_json_within_limit(self):
        item = self.contract.items.get()
        WorkOrder.objects.bulk_create(
            WorkOrder(
                contract=self.contract,
                item=item,
                number=f"OS-ARISE-LOTE-{index:03d}/2026",
                description="Execução exclusivamente fictícia",
                hours=Decimal("1.0000"),
                unit_value=item.unit_value,
                unit_name=item.unit_display,
                responsible="Responsável fictício",
                opening_date=date(2026, 1, 10),
                deadline=date(2027, 1, 31),
                status=WorkOrderStatus.OPEN,
                process_number=f"PROC-LOTE-{index:03d}",
                created_by=self.fiscal,
            )
            for index in range(60)
        )
        text = authorized_data(self.auxiliary, route="assistant:chat")
        self.assertLessEqual(len(text), MAX_DATA_CHARS)
        payload = json.loads(text)
        self.assertEqual(payload["resumo_os_abertas"]["os_abertas"], 61)
        self.assertIn("Lista limitada", payload["observacao"])

    def test_fiscal_and_contract_manager_keep_contract_finances(self):
        for user in (self.fiscal, self.contract_manager):
            with self.subTest(profile=user.profile):
                payload = json.loads(authorized_data(user, route="assistant:chat"))
                snapshot = payload["contratos"][0]
                self.assertEqual(snapshot["contrato"]["numero"], self.contract.number)
                financial = snapshot["financeiro"]
                self.assertEqual(financial["valor_atual"], "R$ 100.000,00")
                for key in ("empenhado", "pago", "saldo_contratual"):
                    self.assertIn(key, financial)
                    self.assertTrue(financial[key]["valor"].startswith("R$ "))
                self.assertEqual(snapshot["itens"][0]["valor_unitario"], "R$ 250,00")
                self.assertEqual(snapshot["itens"][0]["quantidade_contratada"], "500.0000")
                self.assertEqual(len(snapshot["ordens_servico_abertas"]), 1)

    def test_administrative_manager_keeps_portfolio_finances(self):
        payload = json.loads(
            authorized_data(self.administrative_manager, route="assistant:chat")
        )
        portfolio = payload["carteira_institucional"]
        self.assertEqual(portfolio["quantidade_contratos"], 1)
        self.assertEqual(portfolio["valor_atual"], "R$ 100.000,00")
        for key in ("empenhado", "pago", "saldo_contratual"):
            self.assertTrue(portfolio[key].startswith("R$ "))
        self.assertEqual(payload["contratos"][0]["valor_atual"], "R$ 100.000,00")
        selected = json.loads(
            authorized_data(
                self.administrative_manager,
                route="assistant:chat",
                contract_id=self.contract.pk,
            )
        )
        self.assertIn("financeiro", selected["contratos"][0])
