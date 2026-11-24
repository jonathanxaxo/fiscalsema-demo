from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile
from core.notifications import build_notifications
from organizations.models import Organization

from .governance import (
    apply_control_pack,
    create_contract_change,
    create_external_record,
    create_obligation,
    create_receipt,
    create_risk,
    governance_snapshot,
    update_alert_policy,
    update_checklist_item,
    void_contract_change,
)
from .models import (
    ChecklistApplicability,
    ChecklistStatus,
    Contract,
    ContractChangeType,
    ContractChangeStatus,
    ContractExternalRecordStatus,
    ContractObligationCategory,
    ContractObligationStatus,
    ContractReceiptResult,
    ContractReceiptType,
    ContractRiskLevel,
    ContractRiskStatus,
)
from .timeline import build_contract_timeline


User = get_user_model()
VALID_PASSWORD = "SenhaMuitoForte!2026"


class ContractGovernanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Organização Demo")
        cls.fiscal = User.objects.create_user(
            email="fiscal.governanca@example.local",
            full_name="Fiscal Governança",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )
        cls.auxiliary = User.objects.create_user(
            email="auxiliar.governanca@example.local",
            full_name="Auxiliar Governança",
            password=VALID_PASSWORD,
            profile=UserProfile.AUXILIARY_ADMINISTRATIVE,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )
        cls.manager = User.objects.create_user(
            email="gestor.governanca@example.local",
            full_name="Gestor Governança",
            password=VALID_PASSWORD,
            profile=UserProfile.ADMINISTRATIVE_MANAGER,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )
        today = timezone.localdate()
        cls.contract = Contract.objects.create(
            number="GOV-001/2026",
            process_number="DEMO-PRO-001",
            object="Serviços fictícios para teste de governança",
            contracting_organization=cls.organization,
            supplier_name="Fornecedor Fictício de Governança",
            supplier_tax_id="12345678000199",
            signature_date=today - timedelta(days=180),
            validity_start=today - timedelta(days=180),
            validity_end=today + timedelta(days=30),
            original_value=Decimal("1000.00"),
            responsible_fiscal=cls.fiscal,
        )

    def test_change_updates_current_value_and_validity_without_overwriting_original(self):
        new_end = self.contract.validity_end + timedelta(days=365)
        change = create_contract_change(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "change_type": "ADITIVO",
                "number": "01/2026",
                "official_date": timezone.localdate(),
                "effective_date": timezone.localdate(),
                "value_delta": Decimal("250.00"),
                "validity_end_after": new_end,
                "source_reference": "Termo aditivo fictício 01/2026",
                "summary": "Ampliação fictícia do valor e da vigência.",
            },
        )
        self.assertEqual(self.contract.original_value, Decimal("1000.00"))
        self.assertEqual(self.contract.current_value, Decimal("1250.00"))
        self.assertEqual(self.contract.current_validity_end, new_end)

        void_contract_change(
            change_id=change.pk,
            contract_id=self.contract.pk,
            actor=self.fiscal,
            reason="Instrumento fictício anulado para teste.",
        )
        change.refresh_from_db()
        self.assertEqual(change.status, ContractChangeStatus.VOIDED)
        self.assertEqual(self.contract.current_value, Decimal("1000.00"))
        self.assertEqual(self.contract.current_validity_end, self.contract.validity_end)
        with self.assertRaises(ValidationError):
            change.delete()

    def test_future_change_does_not_affect_current_position_before_effective_date(self):
        create_contract_change(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "change_type": ContractChangeType.EXTENSION,
                "number": "FUTURO-01/2026",
                "official_date": timezone.localdate(),
                "effective_date": timezone.localdate() + timedelta(days=10),
                "value_delta": Decimal("500.00"),
                "validity_end_after": self.contract.validity_end + timedelta(days=365),
                "source_reference": "Instrumento futuro fictício",
                "summary": "Efeitos futuros para teste.",
            },
        )
        self.assertEqual(self.contract.current_value, self.contract.original_value)
        self.assertEqual(self.contract.current_validity_end, self.contract.validity_end)

    def test_contract_list_year_filter_uses_current_validity(self):
        new_end = self.contract.validity_end + timedelta(days=365)
        create_contract_change(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "change_type": ContractChangeType.EXTENSION,
                "number": "PRORROGACAO-01/2026",
                "official_date": timezone.localdate(),
                "effective_date": timezone.localdate(),
                "value_delta": Decimal("0.00"),
                "validity_end_after": new_end,
                "source_reference": "Instrumento fictício de prorrogação",
                "summary": "Prorrogação usada no filtro por exercício.",
            },
        )
        client = Client()
        client.force_login(self.fiscal)
        response = client.get(reverse("contracts:list"), {"exercicio": str(new_end.year)})
        self.assertContains(response, self.contract.number)

    def test_confirmed_alert_policy_and_due_obligation_reach_notifications(self):
        update_alert_policy(contract_id=self.contract.pk, actor=self.fiscal, days=[30, 15])
        create_obligation(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "title": "Conferir certidão fictícia",
                "category": ContractObligationCategory.ADMINISTRATIVE,
                "due_date": timezone.localdate(),
                "responsible": "Fiscal responsável",
                "source_reference": "Cláusula fictícia 8.1",
                "evidence_reference": "",
                "status": ContractObligationStatus.PENDING,
                "notes": "",
            },
        )
        notifications = build_notifications(self.fiscal, contract_id=self.contract.pk)
        titles = {item["title"] for item in notifications["items"]}
        self.assertTrue(any("Vigência termina em" in title for title in titles))
        self.assertTrue(any("Conferir certidão fictícia" in title for title in titles))

        auxiliary_notifications = build_notifications(
            self.auxiliary, contract_id=self.contract.pk
        )
        self.assertTrue(
            any(
                "Conferir certidão fictícia" in item["title"]
                for item in auxiliary_notifications["items"]
            )
        )

    def test_control_pack_is_idempotent_and_requires_human_confirmation(self):
        pack, created = apply_control_pack(
            contract_id=self.contract.pk, actor=self.fiscal, pack_code="TIC"
        )
        self.assertEqual(pack.code, "TIC")
        self.assertEqual(created, 9)
        _, created_again = apply_control_pack(
            contract_id=self.contract.pk, actor=self.fiscal, pack_code="TIC"
        )
        self.assertEqual(created_again, 0)
        item = self.contract.checklist_items.get(code="TIC-01")
        self.assertEqual(item.applicability, ChecklistApplicability.TO_CONFIRM)

        update_checklist_item(
            item_id=item.pk,
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "applicability": ChecklistApplicability.APPLICABLE,
                "status": ChecklistStatus.COMPLETED,
                "due_date": None,
                "evidence_reference": "Processo fictício, documento 10",
                "notes": "Conferido manualmente no teste.",
            },
        )
        item.refresh_from_db()
        self.assertEqual(item.status, ChecklistStatus.COMPLETED)

    def test_receipt_risk_and_external_tracking_are_auditable(self):
        receipt = create_receipt(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "receipt_type": ContractReceiptType.PROVISIONAL,
                "receipt_date": timezone.localdate(),
                "result": ContractReceiptResult.ACCEPTED,
                "object_reference": "Entrega fictícia 01",
                "term_reference": "Termo fictício de recebimento provisório",
                "reservations": "",
            },
        )
        risk = create_risk(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "title": "Atraso fictício na entrega",
                "probability": ContractRiskLevel.MEDIUM,
                "impact": ContractRiskLevel.HIGH,
                "response": "Acompanhar o cronograma e registrar ocorrências.",
                "owner": "Fiscal responsável",
                "source_reference": "Mapa de riscos fictício",
                "review_date": timezone.localdate(),
                "status": ContractRiskStatus.OPEN,
            },
        )
        external = create_external_record(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "system": "SIAG",
                "label": "Registro fictício do contrato",
                "reference": "",
                "required": True,
                "due_date": timezone.localdate(),
                "status": ContractExternalRecordStatus.PENDING,
                "source_reference": "Controle fictício confirmado no teste",
                "notes": "",
            },
        )
        self.assertIsNotNone(receipt.pk)
        self.assertIsNotNone(risk.pk)
        self.assertIsNotNone(external.pk)
        timeline_titles = {entry.title for entry in build_contract_timeline(self.contract)}
        self.assertIn("Recebimento registrado", timeline_titles)
        self.assertIn("Risco cadastrado", timeline_titles)
        self.assertIn("Registro externo cadastrado", timeline_titles)

    def test_auxiliary_snapshot_hides_technical_governance(self):
        create_risk(
            contract_id=self.contract.pk,
            actor=self.fiscal,
            data={
                "title": "Risco técnico fictício",
                "probability": ContractRiskLevel.LOW,
                "impact": ContractRiskLevel.MEDIUM,
                "response": "Monitorar.",
                "owner": "Fiscal",
                "source_reference": "Mapa fictício",
                "review_date": None,
                "status": ContractRiskStatus.MONITORING,
            },
        )
        snapshot = governance_snapshot(self.contract, self.auxiliary)
        self.assertTrue(snapshot["limited_auxiliary"])
        self.assertFalse(snapshot["can_edit"])
        self.assertEqual(snapshot["risks"].count(), 0)
        self.assertEqual(tuple(snapshot["packs"]), ())
        client = Client()
        client.force_login(self.auxiliary)
        response = client.get(reverse("contracts:governance", args=[self.contract.pk]))
        self.assertNotContains(response, "Risco técnico fictício")
        self.assertNotContains(response, "Riscos abertos")
        self.assertNotContains(response, "Checklist pendente")

    def test_governance_records_require_evidence_or_justification(self):
        with self.assertRaises(ValidationError):
            create_obligation(
                contract_id=self.contract.pk,
                actor=self.fiscal,
                data={
                    "title": "Obrigação concluída sem prova",
                    "category": ContractObligationCategory.DOCUMENTARY,
                    "due_date": timezone.localdate(),
                    "responsible": "Fiscal",
                    "source_reference": "Fonte fictícia",
                    "evidence_reference": "",
                    "status": ContractObligationStatus.COMPLETED,
                    "notes": "",
                },
            )
        with self.assertRaises(ValidationError):
            create_receipt(
                contract_id=self.contract.pk,
                actor=self.fiscal,
                data={
                    "receipt_type": ContractReceiptType.PROVISIONAL,
                    "receipt_date": timezone.localdate(),
                    "result": ContractReceiptResult.REJECTED,
                    "object_reference": "Entrega fictícia",
                    "term_reference": "Termo fictício",
                    "reservations": "",
                },
            )
        with self.assertRaises(ValidationError):
            create_external_record(
                contract_id=self.contract.pk,
                actor=self.fiscal,
                data={
                    "system": "SIGADOC",
                    "label": "Registro sem referência",
                    "reference": "",
                    "required": True,
                    "due_date": timezone.localdate(),
                    "status": ContractExternalRecordStatus.REGISTERED,
                    "source_reference": "Fonte fictícia",
                    "notes": "",
                },
            )

    def test_manager_can_read_but_cannot_post_and_unrelated_fiscal_gets_404(self):
        client = Client()
        client.force_login(self.manager)
        url = reverse("contracts:governance", args=[self.contract.pk])
        self.assertEqual(client.get(url).status_code, 200)
        write_url = reverse("contracts:obligation_create", args=[self.contract.pk])
        self.assertEqual(client.get(write_url).status_code, 403)
        self.assertEqual(
            client.post(write_url, {}).status_code,
            403,
        )

        other = User.objects.create_user(
            email="outro.fiscal.governanca@example.local",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=self.organization,
        )
        client.force_login(other)
        self.assertEqual(client.get(url).status_code, 404)

    def test_non_fiscal_cannot_apply_pack_through_service(self):
        with self.assertRaises(PermissionDenied):
            apply_control_pack(
                contract_id=self.contract.pk, actor=self.manager, pack_code="TIC"
            )
