from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile
from accounts.services import change_user_profile
from assistant.ferramentas import authorized_data
from organizations.models import Organization

from .intelligence import (
    CALCULATOR_QUANTITY_X_UNIT_VALUE,
    calculate_with_confirmed_rule,
    confirm_contract_classification,
    confirm_item_classification,
    create_contract_rule_candidate,
    detect_item_modality,
    run_contract_intelligence,
    review_contract_rule,
    transition_finding,
)
from .models import (
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractItem,
    ContractItemUnit,
    ContractFindingStatus,
    ContractModality,
    ContractManagementCategory,
    ContractRuleType,
    FiscalSubstitution,
    FiscalSubstitutionStatus,
    IntelligenceReviewStatus,
)
from .services import (
    contracts_exportable_by,
    contracts_visible_to,
    contracts_writable_by,
    share_contract_read_only,
)
from documents.models import Document, DocumentType, RelatedEntityType
from documents.services import document_metadata_visible_to, documents_visible_to


User = get_user_model()
VALID_PASSWORD = "SenhaMuitoForte!2026"


class IntelligencePureUnitTests(SimpleTestCase):
    def test_classifier_uses_structured_unit_and_does_not_guess_custom_unit(self):
        hourly = SimpleNamespace(
            unit=ContractItemUnit.HOUR,
            get_unit_display=lambda: "Hora",
        )
        custom = SimpleNamespace(
            unit=ContractItemUnit.CUSTOM,
            get_unit_display=lambda: "Personalizada",
        )
        self.assertEqual(detect_item_modality(hourly)[0], ContractModality.HOUR)
        self.assertEqual(detect_item_modality(custom)[0], "")

    def test_only_confirmed_typed_rule_calculates_with_decimal(self):
        rule = SimpleNamespace(
            status=IntelligenceReviewStatus.CONFIRMED,
            calculator_key=CALCULATOR_QUANTITY_X_UNIT_VALUE,
            pk=7,
            code="ITEM-01",
            version=2,
            source_document_id=11,
            source_reference="Cláusula 5.2",
        )
        result = calculate_with_confirmed_rule(
            rule=rule,
            quantity=Decimal("2.5000"),
            unit_value=Decimal("40.00"),
        )
        self.assertEqual(result["valor"], Decimal("100.00"))
        rule.status = IntelligenceReviewStatus.DETECTED
        with self.assertRaisesMessage(ValidationError, "não confirmada"):
            calculate_with_confirmed_rule(
                rule=rule,
                quantity=Decimal("1.0000"),
                unit_value=Decimal("40.00"),
            )

    def test_classifier_covers_all_structured_item_units(self):
        cases = {
            ContractItemUnit.MONTH: ContractModality.MONTHLY,
            ContractItemUnit.HOUR: ContractModality.HOUR,
            ContractItemUnit.UNIT: ContractModality.UNIT,
            ContractItemUnit.SERVICE: ContractModality.SERVICE,
            ContractItemUnit.LICENSE: ContractModality.LICENSE,
            ContractItemUnit.USER: ContractModality.USER,
            ContractItemUnit.CLASS: ContractModality.CLASS,
            ContractItemUnit.PACKAGE: ContractModality.LOT,
            ContractItemUnit.UST: ContractModality.UST,
            ContractItemUnit.HST: ContractModality.HST,
            ContractItemUnit.USN: ContractModality.USN,
        }
        for unit, expected in cases.items():
            with self.subTest(unit=unit):
                item = SimpleNamespace(
                    unit=unit,
                    get_unit_display=lambda current=unit: current,
                )
                self.assertEqual(detect_item_modality(item)[0], expected)


class ProfileAuthorizationAndEngineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name="Organização A")
        cls.org_b = Organization.objects.create(name="Organização B")
        cls.admin = User.objects.create_superuser(
            email="admin@example.local",
            full_name="Administrador",
            password=VALID_PASSWORD,
        )
        cls.fiscal_a = cls._user(
            "fiscal.a@example.local", UserProfile.FISCAL_TITULAR, cls.org_a
        )
        cls.fiscal_b = cls._user(
            "fiscal.b@example.local", UserProfile.FISCAL_TITULAR, cls.org_b
        )
        cls.auxiliary = cls._user(
            "auxiliar@example.local", UserProfile.AUXILIARY_ADMINISTRATIVE, cls.org_a
        )
        cls.administrative_manager = cls._user(
            "gestor.adm@example.local", UserProfile.ADMINISTRATIVE_MANAGER, cls.org_a
        )
        cls.contract_manager = cls._user(
            "gestor.contrato@example.local", UserProfile.CONTRACT_MANAGER, cls.org_a
        )
        cls.substitute = cls._user(
            "substituto@example.local", UserProfile.FISCAL_TITULAR, cls.org_a
        )
        cls.contract_a = cls._contract("A-001/2026", cls.org_a, cls.fiscal_a)
        cls.contract_b = cls._contract("B-001/2026", cls.org_b, cls.fiscal_b)
        cls.archived_contract = cls._contract("ARQ-001/2026", cls.org_b, cls.fiscal_b)
        Contract.objects.filter(pk=cls.archived_contract.pk).update(
            archived_at=timezone.now(),
            archived_by=cls.fiscal_b,
            archive_reason="Encerrado para teste de autorização.",
        )
        ContractAccess.objects.create(
            contract=cls.contract_a,
            user=cls.contract_manager,
            access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE,
            granted_by=cls.fiscal_a,
        )
        today = timezone.localdate()
        FiscalSubstitution.objects.create(
            contract=cls.contract_a,
            substitute=cls.substitute,
            email=cls.substitute.email,
            starts_on=today,
            ends_on=today + timedelta(days=5),
            status=FiscalSubstitutionStatus.LINKED,
            created_by=cls.fiscal_a,
            linked_at=timezone.now(),
        )

    @classmethod
    def _user(cls, email, profile, organization):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0],
            password=VALID_PASSWORD,
            profile=profile,
            status=AccountStatus.ACTIVE,
            organization=organization,
        )

    @classmethod
    def _contract(cls, number, organization, fiscal):
        return Contract.objects.create(
            number=number,
            process_number=f"PROC-{number}",
            object="Serviços fictícios de TIC",
            contracting_organization=organization,
            supplier_name="Fornecedor Fictício",
            supplier_tax_id="12345678000199",
            signature_date=date(2026, 1, 1),
            validity_start=date(2026, 1, 1),
            validity_end=date(2027, 12, 31),
            original_value=Decimal("200.00"),
            responsible_fiscal=fiscal,
        )

    def test_profile_visibility_and_writing_are_enforced_in_backend(self):
        self.assertEqual(
            set(contracts_visible_to(self.auxiliary).values_list("pk", flat=True)),
            {self.contract_a.pk, self.contract_b.pk},
        )
        self.assertEqual(
            set(
                contracts_visible_to(self.administrative_manager).values_list(
                    "pk", flat=True
                )
            ),
            {self.contract_a.pk, self.contract_b.pk},
        )
        self.assertEqual(
            set(contracts_visible_to(self.contract_manager).values_list("pk", flat=True)),
            {self.contract_a.pk},
        )
        self.assertFalse(contracts_writable_by(self.auxiliary).exists())
        self.assertFalse(contracts_writable_by(self.administrative_manager).exists())
        self.assertFalse(contracts_writable_by(self.contract_manager).exists())
        self.assertEqual(
            set(contracts_exportable_by(self.contract_manager).values_list("pk", flat=True)),
            {self.contract_a.pk},
        )
        self.assertEqual(
            set(
                contracts_exportable_by(self.administrative_manager).values_list(
                    "pk", flat=True
                )
            ),
            {self.contract_a.pk, self.contract_b.pk},
        )
        self.assertEqual(
            set(contracts_writable_by(self.substitute).values_list("pk", flat=True)),
            {self.contract_a.pk},
        )

    def test_engine_classifies_mixed_contract_and_records_execution(self):
        hourly_item = ContractItem.objects.create(
            contract=self.contract_a,
            number="01",
            description="Horas técnicas",
            category="TIC",
            unit=ContractItemUnit.HOUR,
            contracted_quantity=Decimal("2.0000"),
            unit_value=Decimal("50.00"),
            created_by=self.fiscal_a,
        )
        ContractItem.objects.create(
            contract=self.contract_a,
            number="02",
            description="Licenças",
            category="TIC",
            unit=ContractItemUnit.LICENSE,
            contracted_quantity=Decimal("2.0000"),
            unit_value=Decimal("50.00"),
            created_by=self.fiscal_a,
        )
        result = run_contract_intelligence(
            contract_id=self.contract_a.pk,
            actor=self.fiscal_a,
        )
        self.assertEqual(result.modality, ContractModality.MIXED)
        self.assertEqual(result.classified_items, 2)
        self.assertEqual(self.contract_a.intelligence_executions.count(), 1)
        execution = self.contract_a.intelligence_executions.get(pk=result.execution_id)
        self.assertEqual(execution.summary["rule_pack"], "BR_TIC_FISCALIZATION")
        classification = confirm_contract_classification(
            contract_id=self.contract_a.pk,
            actor=self.fiscal_a,
            modality=ContractModality.MIXED,
            management_category=ContractManagementCategory.SYSTEM,
        )
        self.assertEqual(classification.management_category, ContractManagementCategory.SYSTEM)
        item_classification = confirm_item_classification(
            contract_id=self.contract_a.pk,
            item_id=hourly_item.pk,
            actor=self.fiscal_a,
            modality=ContractModality.HOUR,
        )
        self.assertEqual(item_classification.status, IntelligenceReviewStatus.CONFIRMED)
        self.assertEqual(item_classification.confirmed_by, self.fiscal_a)

    def test_administrator_reclassifies_profile_and_revokes_incompatible_link(self):
        change_user_profile(
            user_id=self.contract_manager.pk,
            actor=self.admin,
            profile=UserProfile.AUXILIARY_ADMINISTRATIVE,
        )
        self.contract_manager.refresh_from_db()
        access = ContractAccess.objects.get(
            contract=self.contract_a, user=self.contract_manager
        )
        self.assertEqual(self.contract_manager.profile, UserProfile.AUXILIARY_ADMINISTRATIVE)
        self.assertEqual(access.status, ContractAccessStatus.REVOKED)

    def test_fiscal_can_link_contract_manager_without_granting_write(self):
        access, invitation = share_contract_read_only(
            contract_id=self.contract_b.pk,
            actor=self.fiscal_b,
            email=self.contract_manager.email,
        )
        self.assertIsNone(invitation)
        self.assertEqual(access.status, ContractAccessStatus.ACTIVE)
        self.assertEqual(access.access_type, ContractAccessType.READ_ONLY)
        self.assertEqual(access.granted_by, self.fiscal_b)
        self.assertFalse(contracts_writable_by(self.contract_manager).exists())

    def test_auxiliary_sees_document_metadata_but_not_private_file(self):
        document = Document.objects.bulk_create([
            Document(
                contract=self.contract_a,
                title="Contrato fictício",
                document_type=DocumentType.CONTRACT,
                origin="Teste",
                related_entity_type=RelatedEntityType.CONTRACT,
                file="documents/teste.pdf",
                original_name="contrato.pdf",
                mime_type="application/pdf",
                file_size=100,
                sha256="a" * 64,
                uploaded_by=self.fiscal_a,
            )
        ])[0]
        self.assertTrue(document_metadata_visible_to(self.auxiliary).filter(pk=document.pk).exists())
        self.assertFalse(documents_visible_to(self.auxiliary).filter(pk=document.pk).exists())
        self.assertTrue(documents_visible_to(self.contract_manager).filter(pk=document.pk).exists())
        self.client.force_login(self.auxiliary)
        response = self.client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(response.status_code, 404)

    def test_auxiliary_can_request_scan_without_receiving_operational_write(self):
        result = run_contract_intelligence(
            contract_id=self.contract_b.pk,
            actor=self.auxiliary,
        )
        self.assertEqual(result.contract_id, self.contract_b.pk)
        self.assertFalse(contracts_writable_by(self.auxiliary).exists())

    def test_rule_requires_document_and_human_confirmation(self):
        document = Document.objects.bulk_create([
            Document(
                contract=self.contract_a,
                title="Termo de Referência fictício",
                document_type=DocumentType.TERMS_OF_REFERENCE,
                origin="Teste",
                related_entity_type=RelatedEntityType.CONTRACT,
                file="documents/tr-teste.pdf",
                original_name="tr.pdf",
                mime_type="application/pdf",
                file_size=100,
                sha256="b" * 64,
                uploaded_by=self.fiscal_a,
            )
        ])[0]
        rule = create_contract_rule_candidate(
            contract_id=self.contract_a.pk,
            actor=self.fiscal_a,
            code="ITEM-01",
            name="Cálculo do item",
            description="Quantidade executada multiplicada pelo valor unitário.",
            rule_type=ContractRuleType.CALCULATION,
            source_document=document,
            source_reference="Item 5.2",
            calculator_key=CALCULATOR_QUANTITY_X_UNIT_VALUE,
            formula_description="quantidade × valor unitário",
        )
        self.assertEqual(rule.status, IntelligenceReviewStatus.AWAITING_CONFIRMATION)
        with self.assertRaisesMessage(ValidationError, "não confirmada"):
            calculate_with_confirmed_rule(
                rule=rule, quantity=Decimal("1.0000"), unit_value=Decimal("10.00")
            )
        rule = review_contract_rule(rule_id=rule.pk, actor=self.fiscal_a, action="confirm")
        self.assertEqual(rule.status, IntelligenceReviewStatus.CONFIRMED)
        result = calculate_with_confirmed_rule(
            rule=rule, quantity=Decimal("2.0000"), unit_value=Decimal("10.00")
        )
        self.assertEqual(result["valor"], Decimal("20.00"))

    def test_arise_receives_only_contracts_visible_to_the_profile(self):
        data = authorized_data(self.contract_manager, route="assistant:chat")
        self.assertIn(self.contract_a.number, data)
        self.assertNotIn(self.contract_b.number, data)
        unauthorized = authorized_data(
            self.contract_manager,
            route="assistant:chat",
            contract_id=self.contract_b.pk,
        )
        self.assertNotIn(self.contract_b.number, unauthorized)
        self.assertIn("Nenhum contrato autorizado", unauthorized)

    def test_read_only_manager_opening_intelligence_does_not_change_finding(self):
        run_contract_intelligence(contract_id=self.contract_a.pk, actor=self.fiscal_a)
        finding = self.contract_a.intelligence_findings.order_by("pk").first()
        self.assertEqual(finding.status, ContractFindingStatus.NEW)
        self.client.force_login(self.contract_manager)
        response = self.client.get(
            reverse("contracts:intelligence", args=[self.contract_a.pk])
        )
        self.assertEqual(response.status_code, 200)
        finding.refresh_from_db()
        self.assertEqual(finding.status, ContractFindingStatus.NEW)
        self.assertIsNone(finding.read_by_id)
        with self.assertRaises(PermissionDenied):
            transition_finding(
                finding_id=finding.pk,
                actor=self.contract_manager,
                status=ContractFindingStatus.READ,
            )

    def test_item_total_finding_is_resolved_by_reprocessing(self):
        first = ContractItem.objects.create(
            contract=self.contract_a,
            number="01",
            description="Primeiro item",
            category="TIC",
            unit=ContractItemUnit.UNIT,
            contracted_quantity=Decimal("1.0000"),
            unit_value=Decimal("100.00"),
            created_by=self.fiscal_a,
        )
        second = ContractItem.objects.create(
            contract=self.contract_a,
            number="02",
            description="Segundo item para completar o valor",
            category="TIC",
            unit=ContractItemUnit.UNIT,
            contracted_quantity=Decimal("1.0000"),
            unit_value=Decimal("50.00"),
            created_by=self.fiscal_a,
        )
        run_contract_intelligence(contract_id=self.contract_a.pk, actor=self.fiscal_a)
        finding = self.contract_a.intelligence_findings.get(
            code="ITEM_TOTAL_DIVERGENT"
        )
        self.assertEqual(finding.status, ContractFindingStatus.NEW)

        second.unit_value = Decimal("100.00")
        second.save(update_fields=("unit_value", "updated_at"))
        run_contract_intelligence(contract_id=self.contract_a.pk, actor=self.fiscal_a)
        finding.refresh_from_db()
        self.assertEqual(finding.status, ContractFindingStatus.RESOLVED)
        self.assertIn("Reprocessamento determinístico", finding.resolution_justification)
        self.assertTrue(first.is_active)
