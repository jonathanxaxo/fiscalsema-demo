from copy import deepcopy
import hashlib
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from documents.models import Document, DocumentType, RelatedEntityType

from .drafts import confirm_assistant_draft, confirm_assistant_draft_batch
from .models import AssistantDraft, AssistantDraftEvent
from .tests import ControlledAssistantDraftTests


class OperationalAssistantTests(ControlledAssistantDraftTests):
    def setUp(self):
        super().setUp()
        self._media_directory = tempfile.TemporaryDirectory()
        self._media_override = override_settings(MEDIA_ROOT=self._media_directory.name)
        self._media_override.enable()
        self.addCleanup(self._media_override.disable)
        self.addCleanup(self._media_directory.cleanup)

    def update_contract_payload(self, **overrides):
        payload = {
            "entity_type": "CONTRATO",
            "operation": "ATUALIZAR",
            "context": {"target_id": self.contract.pk},
            "payload": {"notes": "Atualização extraída do documento autorizado."},
            "evidence": [{
                "source": "Documento oficial informado pelo Fiscal",
                "reference": "DOC-OPERACIONAL-001",
                "field": "notes",
                "extracted_value": "Atualização extraída do documento autorizado.",
                "confidence": "ENCONTRADO_EM_FONTE",
                "validation_result": "PENDENTE_DE_CONFIRMACAO",
            }],
            "source_summary": "Comparação feita contra o cadastro vigente.",
            "source_authority": "DOCUMENTO_OFICIAL_VALIDADO",
            "confidence_level": "ENCONTRADO_EM_FONTE",
        }
        payload.update(overrides)
        return payload

    def test_update_is_only_a_draft_until_human_confirms(self):
        response = self.create_draft(self.update_contract_payload())
        self.assertEqual(response.status_code, 201, response.content)
        draft = AssistantDraft.objects.get(pk=response.json()["data"]["id"])
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "")
        self.assertEqual(draft.operation, AssistantDraft.Operation.UPDATE)
        self.assertEqual(draft.target_id, self.contract.pk)
        self.assertEqual(draft.comparison[0]["classification"], "NOVO")
        self.assertTrue(draft.requires_human_confirmation)

        self.client.force_login(self.owner)
        response = self.client.post(f"/rascunhos-ia/{draft.pk}/confirmar/")
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        draft.refresh_from_db()
        self.assertEqual(
            self.contract.notes, "Atualização extraída do documento autorizado."
        )
        self.assertEqual(draft.consistency_result["status"], "VALIDADO")
        self.assertEqual(draft.consistency_result["contract_id"], self.contract.pk)
        self.assertTrue(AssistantDraftEvent.objects.filter(
            draft=draft,
            event_type=AssistantDraftEvent.EventType.CONFIRMED,
            details__confirmacao_humana=True,
        ).exists())

    def test_critical_change_is_classified_as_divergent(self):
        body = self.update_contract_payload()
        body["payload"] = {"original_value": "110000,00"}
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 201, response.content)
        comparison = response.json()["data"]["comparison"][0]
        self.assertEqual(comparison["classification"], "DIVERGENTE")
        self.assertTrue(comparison["critical"])
        self.assertEqual(comparison["source_precedence"], "CONFIRMACAO_OBRIGATORIA")
        self.contract.refresh_from_db()
        self.assertEqual(str(self.contract.original_value), "100000.00")

    def test_equal_value_is_identified_without_writing(self):
        body = self.update_contract_payload()
        body["payload"] = {"number": self.contract.number}
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            response.json()["data"]["comparison"][0]["classification"], "IGUAL"
        )

    def test_low_confidence_value_is_never_treated_as_reliable(self):
        body = self.update_contract_payload(confidence_level="ESTIMADO")
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            response.json()["data"]["comparison"][0]["classification"],
            "NAO_CONFIAVEL",
        )

    def test_concurrent_change_blocks_confirmation_without_overwrite(self):
        draft = AssistantDraft.objects.get(
            pk=self.create_draft(self.update_contract_payload()).json()["data"]["id"]
        )
        self.contract.notes = "Alteração humana concorrente."
        self.contract.save(update_fields=("notes",))
        with self.assertRaises(ValidationError):
            confirm_assistant_draft(draft_id=draft.pk, actor=self.owner)
        self.contract.refresh_from_db()
        draft.refresh_from_db()
        self.assertEqual(self.contract.notes, "Alteração humana concorrente.")
        self.assertEqual(draft.status, AssistantDraft.Status.PENDING)

    def test_user_outside_contract_scope_cannot_propose_update(self):
        from .services import create_api_credential

        credential, token = create_api_credential(
            name="IA de outro usuário", authorized_user=self.other, actor=self.admin,
            access_mode=self.credential.AccessMode.CONTROLLED_DRAFT,
        )
        self.assertIsNotNone(credential.pk)
        response = self.create_draft(self.update_contract_payload(), token=token)
        self.assertEqual(response.status_code, 403)

    def test_batch_creation_is_atomic_when_one_proposal_is_invalid(self):
        valid = self.contract_payload()
        invalid = deepcopy(valid)
        invalid["payload"]["number"] = "039/2026"
        invalid["payload"]["validity_end"] = "2025-01-01"
        before = AssistantDraft.objects.count()
        response = self.client.post(
            "/api/v1/drafts/batch/",
            data={"proposals": [valid, invalid]},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(AssistantDraft.objects.count(), before)

    def test_batch_confirmation_rolls_back_all_if_one_draft_becomes_invalid(self):
        first = self.contract_payload()
        second = deepcopy(first)
        second["payload"]["number"] = "039/2026"
        response = self.client.post(
            "/api/v1/drafts/batch/", data={"proposals": [first, second]},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.token}",
        )
        self.assertEqual(response.status_code, 201, response.content)
        drafts = list(AssistantDraft.objects.filter(batch_id=response.json()["batch_id"]).order_by("pk"))
        broken_payload = dict(drafts[1].payload)
        broken_payload["validity_end"] = "2025-01-01"
        AssistantDraft.objects.filter(pk=drafts[1].pk).update(payload=broken_payload)
        before = self.contract.__class__.objects.count()
        with self.assertRaises(ValidationError):
            confirm_assistant_draft_batch(batch_id=drafts[0].batch_id, actor=self.owner)
        self.assertEqual(self.contract.__class__.objects.count(), before)
        self.assertFalse(self.contract.__class__.objects.filter(number="038/2026").exists())

    def test_capabilities_expose_update_batch_and_no_direct_database(self):
        response = self.get("/api/v1/capabilities/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(set(data["controlled_operations"]), {"CRIAR", "ATUALIZAR"})
        self.assertTrue(data["transactional_batches"])
        self.assertTrue(data["source_comparison"])
        self.assertTrue(data["optimistic_concurrency_check"])
        self.assertFalse(data["direct_database_access"])

    def test_malformed_ai_field_is_rejected_without_side_effect(self):
        body = self.update_contract_payload()
        body["payload"] = {"derived_balance_from_ai": "999999.99"}
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 400)
        self.assertIn("derived_balance_from_ai", response.json()["error"]["fields"]["payload"])
        self.contract.refresh_from_db()
        self.assertEqual(str(self.contract.original_value), "100000.00")

    def test_integration_cannot_claim_system_homologated_authority(self):
        body = self.update_contract_payload(source_authority="SISTEMA_HOMOLOGADO")
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AssistantDraft.objects.count(), 0)

    def test_end_to_end_authorized_document_proposal_confirmation_and_query(self):
        content = b"Observacao oficial: conferencia documental concluida."
        document = Document.objects.create(
            contract=self.contract, title="Documento oficial de conferência",
            document_type=DocumentType.CONTRACT, origin="Fiscal responsável",
            related_entity_type=RelatedEntityType.CONTRACT,
            file=SimpleUploadedFile("conferencia.txt", content, content_type="text/plain"),
            original_name="conferencia.txt", mime_type="text/plain",
            file_size=len(content), sha256=hashlib.sha256(content).hexdigest(),
            uploaded_by=self.owner,
        )
        body = self.update_contract_payload()
        body["evidence"] = [{
            "source": "Documento autorizado no FiscalSema Light",
            "document_id": document.pk,
            "field": "notes",
            "extracted_value": body["payload"]["notes"],
            "confidence": "ENCONTRADO_EM_FONTE",
            "validation_result": "PENDENTE_DE_CONFIRMACAO",
        }]
        response = self.create_draft(body)
        self.assertEqual(response.status_code, 201, response.content)
        draft = AssistantDraft.objects.get(pk=response.json()["data"]["id"])
        self.assertEqual(draft.evidence[0]["document_sha256"], document.sha256)
        self.assertEqual(draft.evidence[0]["filename"], "conferencia.txt")

        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.post(f"/rascunhos-ia/{draft.pk}/confirmar/").status_code, 302
        )
        draft.refresh_from_db()
        self.assertEqual(draft.consistency_result["status"], "VALIDADO")
        self.assertTrue(draft.consistency_result["accountability_matches"])

        self.client.logout()
        detail = self.get(f"/api/v1/contracts/{self.contract.pk}/")
        summary = self.get(f"/api/v1/contracts/{self.contract.pk}/summary/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(summary.status_code, 200)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "Atualização extraída do documento autorizado.")
        self.assertEqual(detail.json()["data"]["number"], self.contract.number)
        self.assertEqual(
            summary.json()["data"]["financial"],
            draft.consistency_result["financial_position"],
        )
        event = AssistantDraftEvent.objects.get(
            draft=draft, event_type=AssistantDraftEvent.EventType.CONFIRMED,
        )
        self.assertEqual(
            event.details["valor_efetivamente_gravado"]["notes"],
            "Atualização extraída do documento autorizado.",
        )
