from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import AccountStatus, UserProfile
from organizations.models import Organization

from .models import Contract, ContractEvent, ContractStatus
from .services import correct_contract_registration, create_contract, update_contract


User = get_user_model()
VALID_PASSWORD = "SenhaMuitoForte!2026"


def contract_data(**overrides):
    data = {
        "number": "001/2099",
        "process_number": "PROCESSO-001",
        "object": "Prestação de serviços técnicos",
        "supplier_name": "Fornecedor de Teste",
        "supplier_tax_id": "12345678000199",
        "signature_date": date(2026, 1, 10),
        "validity_start": date(2026, 1, 10),
        "validity_end": date(2027, 1, 9),
        "original_value": Decimal("100000.00"),
        "status": ContractStatus.ACTIVE,
        "notes": "",
    }
    data.update(overrides)
    return data


class ContractModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Contratante")
        self.fiscal = User.objects.create_user(
            email="modelo.contrato@example.local",
            full_name="Fiscal Modelo",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )

    def build_contract(self, **overrides):
        return Contract.objects.create(
            **contract_data(**overrides),
            contracting_organization=self.organization,
            responsible_fiscal=self.fiscal,
        )

    def test_contract_normalizes_text_and_current_value_equals_original(self):
        contract = self.build_contract(
            number="  001/2099  ",
            object="  Serviço   técnico  ",
            supplier_name="  Fornecedor   Teste  ",
        )
        self.assertEqual(contract.number, "001/2099")
        self.assertEqual(contract.object, "Serviço técnico")
        self.assertEqual(contract.supplier_name, "Fornecedor Teste")
        self.assertEqual(contract.current_value, Decimal("100000.00"))

    def test_validity_order_and_negative_value_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.build_contract(validity_end=date(2025, 12, 31))
        with self.assertRaises(ValidationError):
            self.build_contract(original_value=Decimal("-0.01"))

    def test_responsible_must_be_fiscal(self):
        administrator = User.objects.create_superuser(
            email="admin.modelo@example.local",
            full_name="Administrador Modelo",
            password=VALID_PASSWORD,
        )
        with self.assertRaisesMessage(ValidationError, "perfil Fiscal"):
            Contract.objects.create(
                **contract_data(),
                contracting_organization=self.organization,
                responsible_fiscal=administrator,
            )

    def test_number_is_not_made_globally_unique_without_official_rule(self):
        self.build_contract()
        second = self.build_contract(process_number="PROCESSO-002")
        self.assertEqual(Contract.objects.filter(number="001/2099").count(), 2)
        self.assertNotEqual(second.pk, 0)


class ContractAccessTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização")
        self.owner = User.objects.create_user(
            email="dono@example.local",
            full_name="Fiscal Responsável",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="outro@example.local",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.contratos@example.local",
            full_name="Administrador Contratos",
            password=VALID_PASSWORD,
        )
        self.manager = User.objects.create_user(
            email="gestor.contratos@example.local",
            full_name="Administrador de Contratos",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
        )
        self.contract = create_contract(actor=self.owner, **contract_data())
        self.client = Client()

    def test_fiscal_creates_own_contract_with_audit(self):
        self.assertEqual(self.contract.responsible_fiscal, self.owner)
        self.assertEqual(self.contract.contracting_organization, self.organization)
        event = ContractEvent.objects.get(
            event_type=ContractEvent.EventType.CREATED,
            contract=self.contract,
        )
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.details["atual"]["valor_original"], "100000.00")

    def test_owner_sees_and_updates_contract_with_audit(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse("contracts:list")), "001/2099")
        self.assertEqual(
            self.client.get(reverse("contracts:detail", args=[self.contract.pk])).status_code,
            200,
        )
        changed = contract_data(
            number=self.contract.number,
            original_value=Decimal("120000.00"),
            status=ContractStatus.SUSPENDED,
        )
        response = self.client.post(
            reverse("contracts:update", args=[self.contract.pk]),
            {
                key: (
                    value.isoformat()
                    if isinstance(value, date)
                    else "120000,00"
                    if key == "original_value"
                    else value
                )
                for key, value in changed.items()
            },
        )
        self.assertRedirects(response, reverse("contracts:detail", args=[self.contract.pk]))
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.current_value, Decimal("120000.00"))
        self.assertTrue(ContractEvent.objects.filter(
            contract=self.contract,
            event_type=ContractEvent.EventType.STATUS_CHANGED,
            actor=self.owner,
        ).exists())

    def test_contract_update_preserves_localized_money_and_iso_dates(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("contracts:update", args=[self.contract.pk]))

        form = response.context["form"]
        self.assertEqual(form["signature_date"].value(), date(2026, 1, 10))
        self.assertEqual(form["validity_start"].value(), date(2026, 1, 10))
        self.assertEqual(form["validity_end"].value(), date(2027, 1, 9))
        self.assertIn('value="2026-01-10"', str(form["signature_date"]))
        self.assertIn('value="2026-01-10"', str(form["validity_start"]))
        self.assertIn('value="2027-01-09"', str(form["validity_end"]))
        self.assertEqual(form["original_value"].value(), Decimal("100000.00"))
        self.assertIn('value="100.000,00"', str(form["original_value"]))
        self.assertEqual(form.fields["original_value"].widget.input_type, "text")
        self.assertEqual(
            form.fields["original_value"].widget.attrs["inputmode"],
            "decimal",
        )

    def test_only_administrator_can_apply_audited_structural_correction(self):
        with self.assertRaises(PermissionDenied):
            correct_contract_registration(
                contract_id=self.contract.pk,
                actor=self.owner,
                number="001/2099/DEMO",
                source_reference="Planilha oficial",
                reason="Correção de transcrição",
                confirmed=True,
            )

        administrator = User.objects.create_superuser(
            email="admin.correcao@example.local",
            full_name="Administrador da Correção",
            password=VALID_PASSWORD,
        )
        corrected = correct_contract_registration(
            contract_id=self.contract.pk,
            actor=administrator,
            number="001/2099/DEMO",
            signature_date=date(2026, 1, 8),
            validity_start=date(2026, 1, 8),
            source_reference="Planilha oficial de fiscalização",
            reason="Correção de dados comprovados na fonte",
            confirmed=True,
        )

        self.assertEqual(corrected.number, "001/2099/DEMO")
        self.assertEqual(corrected.signature_date, date(2026, 1, 8))
        event = ContractEvent.objects.filter(
            contract=corrected, event_type=ContractEvent.EventType.UPDATED
        ).first()
        self.assertTrue(event.details["correcao_cadastral_auditada"])
        self.assertEqual(event.details["fonte_oficial"], "Planilha oficial de fiscalização")

    def test_other_fiscal_cannot_discover_or_change_contract(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("contracts:list")), "001/2099")
        self.assertEqual(
            self.client.get(reverse("contracts:detail", args=[self.contract.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )
        with self.assertRaises(Contract.DoesNotExist):
            update_contract(contract_id=self.contract.pk, actor=self.other, **contract_data())

    def test_administrator_can_read_all_but_not_operationally_edit(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("contracts:list")), "001/2099")
        response = self.client.get(reverse("contracts:detail", args=[self.contract.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("contracts:update", args=[self.contract.pk]))
        self.assertEqual(self.client.get(reverse("contracts:create")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )

    def test_fiscal_without_active_organization_cannot_create(self):
        self.organization.is_active = False
        self.organization.save()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("contracts:create")).status_code, 403)
        with self.assertRaises(ValidationError):
            create_contract(actor=self.owner, **contract_data(process_number="NOVO"))
        self.assertEqual(
            self.client.get(reverse("contracts:update", args=[self.contract.pk])).status_code,
            404,
        )

    def test_home_shows_empty_state_then_owned_contract(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Você ainda não possui contratos.")
        self.client.force_login(self.owner)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Contrato 001/2099")

    def test_django_admin_is_read_only_and_no_delete_route_exists(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:contracts_contract_add")).status_code, 403)
        self.assertNotIn("delete", [pattern.name for pattern in __import__("contracts.urls").urls.urlpatterns])

    def test_permissions_match_profiles(self):
        self.assertTrue(self.owner.has_perm("contracts.add_contract"))
        self.assertTrue(self.owner.has_perm("contracts.change_contract"))
        self.assertFalse(self.owner.has_perm("contracts.view_all_contracts"))
        self.assertTrue(self.manager.has_perm("contracts.view_all_contracts"))
        self.assertFalse(self.manager.has_perm("contracts.add_contract"))
