from datetime import date
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from accounts.models import AccountStatus, User
from contracts.models import (
    CommitmentMovement,
    Contract,
    ContractAccess,
    ContractAccessStatus,
    ContractAccessType,
    ContractStatus,
)
from contracts.services import create_budget_commitment, create_commitment_movement
from contracts.test_commitments import commitment_data, movement_data
from organizations.models import Organization

from .models import ApiAccessEvent, AssistantDraft, AssistantDraftEvent
from .services import create_api_credential, revoke_api_credential


PASSWORD = "SenhaMuitoForte!2026"


class ApiTestBase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização API")
        self.owner = User.objects.create_user(
            email="owner.api@example.local", full_name="Fiscal API", password=PASSWORD,
            status=AccountStatus.ACTIVE, organization=self.organization,
        )
        self.other = User.objects.create_user(
            email="other.api@example.local", full_name="Outro Fiscal", password=PASSWORD,
            status=AccountStatus.ACTIVE, organization=self.organization,
        )
        self.admin = User.objects.create_superuser(
            email="admin.api@example.local", full_name="Administrador API", password=PASSWORD,
        )
        self.contract = Contract.objects.create(
            number="001/2099", process_number="PROCESSO-API", object="Serviços técnicos",
            contracting_organization=self.organization, supplier_name="Fornecedor",
            supplier_tax_id="12345678000199", signature_date=date(2026, 1, 10),
            validity_start=date(2026, 1, 10), validity_end=date(2027, 1, 9),
            original_value=Decimal("100000.00"), status=ContractStatus.ACTIVE,
            responsible_fiscal=self.owner,
        )
        self.credential, self.token = create_api_credential(
            name="Integração teste", authorized_user=self.owner, actor=self.admin,
        )
        self.client = Client()

    def get(self, path, token=None):
        return self.client.get(path, HTTP_AUTHORIZATION=f"Bearer {token or self.token}")


class SecureReadOnlyApiTests(ApiTestBase):
    def test_token_is_stored_only_as_hash_and_contract_is_visible(self):
        self.assertNotEqual(self.credential.token_hash, self.token)
        self.assertNotIn(self.token, self.credential.token_hash)
        response = self.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], self.contract.pk)
        event = ApiAccessEvent.objects.get(event_type=ApiAccessEvent.EventType.QUERY)
        self.assertEqual(event.actor, self.owner)
        self.assertEqual(event.result_count, 1)

    def test_contract_api_exposes_both_annual_period_dimensions(self):
        response = self.get(f"/api/v1/contracts/{self.contract.pk}/")
        self.assertEqual(response.status_code, 200)
        periods = response.json()["data"]["annual_periods"]
        self.assertEqual(periods["official_closing_rule"], "CALENDAR_YEAR")
        self.assertEqual(len(periods["calendar_years"]), 2)
        self.assertEqual(len(periods["contract_years"]), 1)
        self.assertEqual(periods["calendar_years"][0]["label"], "Fechamento 2026")
        self.assertEqual(periods["contract_years"][0]["label"], "Ano contratual 1")

    def test_commitment_api_exposes_fiscal_year_reversal_and_closure(self):
        commitment = create_budget_commitment(
            contract_id=self.contract.pk,
            actor=self.owner,
            **commitment_data(initial_value=Decimal("100.00")),
        )
        create_commitment_movement(
            commitment_id=commitment.pk,
            actor=self.owner,
            **movement_data(
                movement_type=CommitmentMovement.Type.REVERSAL,
                movement_date=date(2026, 12, 31),
                amount=Decimal("100.00"),
                document_reference="DEMO-DOC-2026/ESTORNO-001",
            ),
        )

        response = self.get(f"/api/v1/contracts/{self.contract.pk}/commitments/")
        self.assertEqual(response.status_code, 200)
        data = response.json()["results"][0]
        self.assertEqual(data["fiscal_year"], 2026)
        self.assertFalse(data["accepts_new_allocations"])
        self.assertEqual(data["closed_for_new_allocations_at"], "2026-12-31")
        self.assertEqual(data["movements"][0]["type"], "ESTORNO")
        self.assertEqual(
            data["movements"][0]["document_reference"],
            "DEMO-DOC-2026/ESTORNO-001",
        )

    def test_read_only_capabilities_never_advertise_drafts(self):
        response = self.get("/api/v1/capabilities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["credential_mode"], "READ_ONLY")
        self.assertEqual(response.json()["controlled_drafts"], [])
        self.assertFalse(response.json()["direct_database_access"])

    def test_missing_or_unknown_token_is_rejected_without_echo(self):
        response = self.client.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "invalid_token")
        unknown = "fsl_000000000000_segredo-que-nao-deve-voltar"
        response = self.get("/api/v1/contracts/", unknown)
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(unknown, response.content.decode())

    def test_scope_is_evaluated_dynamically_and_hidden_resource_returns_404(self):
        other_credential, other_token = create_api_credential(
            name="Escopo outro", authorized_user=self.other, actor=self.admin,
        )
        self.assertEqual(self.get(f"/api/v1/contracts/{self.contract.pk}/", other_token).status_code, 404)
        access = ContractAccess.objects.create(
            contract=self.contract, user=self.other, access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE, granted_by=self.owner,
        )
        self.assertEqual(self.get(f"/api/v1/contracts/{self.contract.pk}/", other_token).status_code, 200)
        access.status = ContractAccessStatus.REVOKED
        access.revoked_by = self.owner
        access.revoked_at = timezone.now()
        access.save()
        self.assertEqual(self.get(f"/api/v1/contracts/{self.contract.pk}/", other_token).status_code, 404)
        self.assertIsNotNone(other_credential.pk)

    def test_unsafe_methods_are_blocked_and_do_not_change_data(self):
        before = Contract.objects.count()
        response = self.client.post(
            "/api/v1/contracts/", data={"number": "X"},
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET")
        self.assertEqual(Contract.objects.count(), before)

    def test_revoked_credential_is_rejected_and_audited(self):
        revoke_api_credential(credential=self.credential, actor=self.admin)
        response = self.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "revoked_token")
        self.assertTrue(ApiAccessEvent.objects.filter(
            event_type=ApiAccessEvent.EventType.DENIED, status_code=401,
        ).exists())

    @override_settings(API_RATE_LIMIT_PER_MINUTE=1)
    def test_rate_limit_returns_429(self):
        self.assertEqual(self.get("/api/v1/contracts/").status_code, 200)
        response = self.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "60")

    def test_pagination_validation_and_financial_notice(self):
        self.assertEqual(self.get("/api/v1/contracts/?page_size=0").status_code, 400)
        response = self.get(f"/api/v1/contracts/{self.contract.pk}/financial-summary/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("revisão humana", response.json()["data"]["decision_notice"])
        self.assertEqual(response.json()["data"]["position"]["contract_balance"]["value"], "100000.00")

    def test_inactive_authorizing_user_invalidates_token_immediately(self):
        self.owner.status = AccountStatus.BLOCKED
        self.owner.save()
        response = self.get("/api/v1/contracts/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "inactive_user")


class ControlledAssistantDraftTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.credential, self.token = create_api_credential(
            name="Rascunhos controlados", authorized_user=self.owner, actor=self.admin,
            access_mode=self.credential.AccessMode.CONTROLLED_DRAFT,
        )

    def contract_payload(self):
        return {
            "entity_type": "CONTRATO",
            "context": {},
            "payload": {
                "number": "038/2026", "process_number": "PROCESSO-RASCUNHO",
                "object": "Serviço proposto pela integração",
                "supplier_name": "Fornecedor", "supplier_tax_id": "12345678000199",
                "signature_date": "2026-02-01", "validity_start": "2026-02-01",
                "validity_end": "2027-01-31", "original_value": "5000,00",
                "status": "ATIVO", "notes": "",
            },
            "evidence": [{"source": "Documento informado pelo Fiscal", "reference": "REF-001"}],
            "source_summary": "Extraído do documento REF-001, sujeito à revisão humana.",
        }

    def create_draft(self, payload=None, token=None):
        return self.client.post(
            "/api/v1/drafts/", data=payload or self.contract_payload(),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token or self.token}",
        )

    def test_all_eight_entity_types_are_declared(self):
        self.assertEqual(set(AssistantDraft.EntityType.values), {
            "CONTRATO", "ITEM", "EMPENHO", "OS", "RATEIO", "EXECUCAO", "NF", "PAGAMENTO",
        })

    def test_read_only_credential_cannot_create_draft(self):
        read_only, token = create_api_credential(
            name="Consulta apenas", authorized_user=self.owner, actor=self.admin,
        )
        self.assertEqual(read_only.access_mode, read_only.AccessMode.READ_ONLY)
        response = self.create_draft(token=token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "insufficient_credential_scope")

    def test_controlled_capabilities_advertise_all_drafts_and_human_confirmation(self):
        response = self.get("/api/v1/capabilities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()["controlled_drafts"]), set(AssistantDraft.EntityType.values))
        self.assertTrue(response.json()["human_confirmation"])

    def test_api_creates_only_draft_and_human_confirmation_creates_record(self):
        before = Contract.objects.count()
        response = self.create_draft()
        self.assertEqual(response.status_code, 201, response.content)
        draft = AssistantDraft.objects.get(pk=response.json()["data"]["id"])
        self.assertEqual(draft.status, AssistantDraft.Status.PENDING)
        self.assertEqual(Contract.objects.count(), before)
        self.client.force_login(self.owner)
        response = self.client.post(f"/rascunhos-ia/{draft.pk}/confirmar/")
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, AssistantDraft.Status.CONFIRMED)
        self.assertEqual(Contract.objects.count(), before + 1)
        self.assertEqual(draft.reviewed_by, self.owner)
        self.assertTrue(AssistantDraftEvent.objects.filter(
            draft=draft, event_type=AssistantDraftEvent.EventType.CONFIRMED,
            details__confirmacao_humana=True,
        ).exists())

    def test_draft_requires_evidence_and_valid_business_fields(self):
        payload = self.contract_payload()
        payload["evidence"] = []
        self.assertEqual(self.create_draft(payload).status_code, 400)
        payload = self.contract_payload()
        payload["payload"]["validity_end"] = "2025-01-01"
        response = self.create_draft(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("fields", response.json()["error"])
        self.assertEqual(AssistantDraft.objects.count(), 0)

    def test_read_only_contract_scope_cannot_create_item_draft(self):
        ContractAccess.objects.create(
            contract=self.contract, user=self.other, access_type=ContractAccessType.READ_ONLY,
            status=ContractAccessStatus.ACTIVE, granted_by=self.owner,
        )
        _credential, token = create_api_credential(
            name="Somente leitura", authorized_user=self.other, actor=self.admin,
            access_mode=self.credential.AccessMode.CONTROLLED_DRAFT,
        )
        response = self.create_draft({
            "entity_type": "ITEM", "context": {"contract_id": self.contract.pk},
            "payload": {}, "evidence": [{"source": "Teste"}], "source_summary": "Teste",
        }, token)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(AssistantDraft.objects.count(), 0)

    def test_other_user_cannot_see_or_confirm_draft(self):
        draft_id = self.create_draft().json()["data"]["id"]
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f"/rascunhos-ia/{draft_id}/").status_code, 404)
        self.assertEqual(self.client.post(f"/rascunhos-ia/{draft_id}/confirmar/").status_code, 404)

    def test_revalidation_blocks_confirmation_and_records_failure(self):
        draft = AssistantDraft.objects.get(pk=self.create_draft().json()["data"]["id"])
        self.owner.status = AccountStatus.BLOCKED
        self.owner.save()
        with self.assertRaises(PermissionDenied):
            from .drafts import confirm_assistant_draft
            confirm_assistant_draft(draft_id=draft.pk, actor=self.owner)
        draft.refresh_from_db()
        self.assertEqual(draft.status, AssistantDraft.Status.PENDING)
        self.assertTrue(AssistantDraftEvent.objects.filter(
            draft=draft, event_type=AssistantDraftEvent.EventType.VALIDATION_FAILED,
        ).exists())

    def test_human_rejection_preserves_draft_and_audit(self):
        draft = AssistantDraft.objects.get(pk=self.create_draft().json()["data"]["id"])
        self.client.force_login(self.owner)
        response = self.client.post(
            f"/rascunhos-ia/{draft.pk}/rejeitar/", {"reason": "Fonte precisa de correção"},
        )
        self.assertEqual(response.status_code, 302)
        draft.refresh_from_db()
        self.assertEqual(draft.status, AssistantDraft.Status.REJECTED)
        self.assertEqual(Contract.objects.filter(number="038/2026").count(), 0)
        self.assertTrue(AssistantDraftEvent.objects.filter(
            draft=draft, event_type=AssistantDraftEvent.EventType.REJECTED,
        ).exists())
