from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import (
    Contract,
    ContractItem,
    ContractItemEvent,
    ContractItemUnit,
)
from .services import create_contract, create_contract_item, update_contract_item
from .tests import VALID_PASSWORD, contract_data


User = get_user_model()


def item_data(**overrides):
    data = {
        "number": "1",
        "external_code": "",
        "description": "Serviço técnico especializado",
        "category": "Serviços",
        "unit": ContractItemUnit.HOUR,
        "custom_unit_name": "",
        "contracted_quantity": Decimal("100.0000"),
        "unit_value": Decimal("250.00"),
        "calculation_rule": "",
        "source_reference": "",
        "is_active": True,
    }
    data.update(overrides)
    return data


class ContractItemModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização de Itens")
        self.fiscal = User.objects.create_user(
            email="modelo.itens@example.local",
            full_name="Fiscal de Itens",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.contract = create_contract(actor=self.fiscal, **contract_data())

    def build_item(self, **overrides):
        return ContractItem.objects.create(
            contract=self.contract,
            created_by=self.fiscal,
            **item_data(**overrides),
        )

    def test_item_normalizes_text_and_calculates_exact_total_with_decimal(self):
        item = self.build_item(
            number="  01  ",
            external_code="  0016243  ",
            description="  Serviço   técnico  ",
            category="  Serviços   especializados ",
            calculation_rule="  Quantidade anual  ×  dois anos  ",
            source_reference="  Planilha   oficial  ",
            contracted_quantity=Decimal("2.5000"),
            unit_value=Decimal("100.00"),
        )
        self.assertEqual(item.number, "01")
        self.assertEqual(item.external_code, "0016243")
        self.assertEqual(item.description, "Serviço técnico")
        self.assertEqual(item.category, "Serviços especializados")
        self.assertEqual(item.calculation_rule, "Quantidade anual × dois anos")
        self.assertEqual(item.source_reference, "Planilha oficial")
        self.assertIsInstance(item.total_value, Decimal)
        self.assertEqual(item.total_value, Decimal("250.00"))

    def test_item_rounds_derived_money_to_cents_half_up(self):
        item = self.build_item(
            number="3",
            contracted_quantity=Decimal("0.0100"),
            unit_value=Decimal("100.50"),
        )
        self.assertEqual(item.total_value, Decimal("1.01"))

    def test_item_number_is_unique_case_insensitively_inside_contract(self):
        self.build_item(number="ITEM-1")
        with self.assertRaises(ValidationError):
            self.build_item(number="item-1")
        second_contract = create_contract(
            actor=self.fiscal,
            **contract_data(process_number="PROCESSO-002"),
        )
        reused = ContractItem.objects.create(
            contract=second_contract,
            created_by=self.fiscal,
            **item_data(number="item-1"),
        )
        self.assertEqual(reused.number, "item-1")

    def test_custom_unit_requires_name_and_standard_unit_clears_it(self):
        with self.assertRaisesMessage(ValidationError, "unidade personalizada"):
            self.build_item(unit=ContractItemUnit.CUSTOM)
        custom = self.build_item(
            number="2",
            unit=ContractItemUnit.CUSTOM,
            custom_unit_name="  Ponto   de função ",
        )
        self.assertEqual(custom.unit_display, "Ponto de função")
        standard = self.build_item(number="3", custom_unit_name="Não deve persistir")
        self.assertEqual(standard.custom_unit_name, "")

    def test_quantity_must_be_positive_and_unit_value_cannot_be_negative(self):
        with self.assertRaises(ValidationError):
            self.build_item(contracted_quantity=Decimal("0"))
        with self.assertRaises(ValidationError):
            self.build_item(unit_value=Decimal("-0.01"))

    def test_annual_reference_and_limit_are_optional_positive_and_auditable(self):
        item = self.build_item(
            annual_reference_quantity=Decimal("3.0000000"),
            annual_reference_unit="  pacote anual de 10 usuários ",
            annual_operational_limit=Decimal("30.0000"),
        )
        self.assertEqual(item.annual_reference_unit, "pacote anual de 10 usuários")
        self.assertEqual(item.annual_operational_limit, Decimal("30.0000"))
        with self.assertRaises(ValidationError):
            self.build_item(number="2", annual_operational_limit=Decimal("0"))


class ContractItemAccessTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Operacional")
        self.owner = User.objects.create_user(
            email="dono.itens@example.local",
            full_name="Fiscal Responsável por Itens",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro.itens@example.local",
            full_name="Outro Fiscal de Itens",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.itens@example.local",
            full_name="Administrador de Itens",
            password=VALID_PASSWORD,
        )
        self.manager = User.objects.create_user(
            email="gestor.itens@example.local",
            full_name="Gestor de Itens",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.item = create_contract_item(
            contract_id=self.contract.pk,
            actor=self.owner,
            **item_data(),
        )
        self.client = Client()

    def test_creation_records_actor_contract_and_derived_total(self):
        self.assertEqual(self.item.contract, self.contract)
        event = ContractItemEvent.objects.get(
            event_type=ContractItemEvent.EventType.CREATED,
            item=self.item,
        )
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.details["atual"]["valor_total_derivado"], "25000.00")

    def test_owner_creates_item_through_localized_form(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("contracts:item_create", args=[self.contract.pk]),
            {
                "number": "2",
                "description": "Segundo item",
                "category": "Serviços",
                "unit": ContractItemUnit.UNIT,
                "custom_unit_name": "",
                "contracted_quantity": "2,5000",
                "unit_value": "100,00",
                "is_active": "on",
            },
        )
        created = ContractItem.objects.get(contract=self.contract, number="2")
        self.assertRedirects(
            response,
            reverse("contracts:item_detail", args=[self.contract.pk, created.pk]),
        )
        self.assertEqual(created.total_value, Decimal("250.00"))

    def test_item_pages_display_money_with_exactly_two_decimal_places(self):
        self.client.force_login(self.owner)

        detail = self.client.get(
            reverse("contracts:item_detail", args=[self.contract.pk, self.item.pk])
        )
        listing = self.client.get(
            reverse("contracts:item_list", args=[self.contract.pk])
        )

        self.assertContains(detail, "R$ 25.000,00")
        self.assertNotContains(detail, "25.000,000000")
        self.assertContains(listing, "R$ 25.000,00")
        self.assertNotContains(listing, "25.000,000000")

    def test_other_fiscal_cannot_discover_or_change_item(self):
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("contracts:item_list", args=[self.contract.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                reverse("contracts:item_detail", args=[self.contract.pk, self.item.pk])
            ).status_code,
            404,
        )
        with self.assertRaises(ContractItem.DoesNotExist):
            update_contract_item(item_id=self.item.pk, actor=self.other, **item_data())

    def test_administrator_reads_items_but_cannot_create_or_edit(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("contracts:item_list", args=[self.contract.pk]))
        self.assertContains(response, self.item.description)
        detail = self.client.get(
            reverse("contracts:item_detail", args=[self.contract.pk, self.item.pk])
        )
        self.assertEqual(detail.status_code, 200)
        self.assertNotContains(
            detail,
            reverse("contracts:item_update", args=[self.contract.pk, self.item.pk]),
        )
        self.assertEqual(
            self.client.get(reverse("contracts:item_create", args=[self.contract.pk])).status_code,
            403,
        )

    def test_inactivation_is_audited_and_not_deleted(self):
        updated = item_data(is_active=False)
        item = update_contract_item(item_id=self.item.pk, actor=self.owner, **updated)
        self.assertFalse(item.is_active)
        self.assertTrue(ContractItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(ContractItemEvent.objects.filter(
            item=item,
            event_type=ContractItemEvent.EventType.DEACTIVATED,
            actor=self.owner,
        ).exists())
        self.assertNotIn(
            "item_delete",
            [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns],
        )

    def test_permissions_match_profiles_and_admin_is_read_only(self):
        self.assertTrue(self.owner.has_perm("contracts.add_contractitem"))
        self.assertTrue(self.owner.has_perm("contracts.change_contractitem"))
        self.assertTrue(self.manager.has_perm("contracts.view_contractitem"))
        self.assertFalse(self.manager.has_perm("contracts.add_contractitem"))
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse("admin:contracts_contractitem_add")).status_code,
            403,
        )
