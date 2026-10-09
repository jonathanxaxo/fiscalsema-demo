import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction
from django.test import override_settings
from django.urls import reverse

from accounts.models import AuthenticationEvent
from contracts.models import ContractEvent, CsvExportEvent, WorkOrderStatus
from contracts.services import share_contract_read_only
from contracts.test_work_orders import WorkOrderBase
from documents.models import DocumentEvent, DocumentType, RelatedEntityType
from documents.services import create_document
from data_imports.models import ImportEvent, SpreadsheetImport
from organizations.models import OrganizationEvent

from .services import build_audit_page


PDF_CONTENT = b"%PDF-1.7\n%%EOF\n"


class AuditTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        self.media_directory = tempfile.mkdtemp(prefix="fiscalsema-audit-")
        self.settings_override = override_settings(MEDIA_ROOT=self.media_directory)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_directory, True)

    def contract_url(self, **params):
        url = reverse("audit:contract", args=[self.contract.pk])
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        return url

    def create_document(self):
        return create_document(
            contract_id=self.contract.pk,
            actor=self.owner,
            file=SimpleUploadedFile("contrato.pdf", PDF_CONTENT, content_type="application/pdf"),
            title="Contrato assinado",
            document_type=DocumentType.CONTRACT,
            origin="SIGADOC",
            related_entity_type=RelatedEntityType.CONTRACT,
            item=None,
            commitment=None,
            work_order=None,
            execution=None,
            invoice=None,
            payment=None,
            previous_version=None,
        )

    def test_owner_sees_consolidated_contract_events(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.contract_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contrato criado")
        self.assertContains(response, "OS criada")
        self.assertContains(response, self.owner.full_name)
        self.assertContains(response, self.organization.name)

    def test_read_only_and_foreign_fiscal_cannot_open_contract_audit(self):
        share_contract_read_only(
            contract_id=self.contract.pk, actor=self.owner, email=self.other.email
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.contract_url()).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.contract_url()).status_code, 302)

    def test_administrator_can_open_global_and_contract_audit(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.get(reverse("audit:global")).status_code, 200)
        self.assertContains(self.client.get(self.contract_url()), "Contrato criado")

    def test_fiscal_cannot_open_global_audit(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("audit:global")).status_code, 403)

    def test_global_audit_includes_authentication_and_organization_events(self):
        AuthenticationEvent.objects.create(
            event_type=AuthenticationEvent.EventType.LOGIN_SUCCESS,
            user=self.owner,
            details={"resultado": "sucesso"},
        )
        OrganizationEvent.objects.create(
            event_type=OrganizationEvent.EventType.ORGANIZATION_CREATED,
            actor=self.manager,
            organization=self.organization,
            details={"atual": {"nome": self.organization.name}},
        )
        self.assertEqual(OrganizationEvent.objects.count(), 1)
        audit_page = build_audit_page(filters={}, page_number=None, include_global=True)
        self.assertIn("ORGANIZACAO", {entry.category for entry in audit_page.object_list})
        self.client.force_login(self.manager)
        response = self.client.get(reverse("audit:global"))
        self.assertContains(response, "Login realizado")
        self.assertContains(response, "Organização criada")

    def test_contract_audit_includes_spreadsheet_import_events(self):
        spreadsheet_import = SpreadsheetImport.objects.create(
            contract=self.contract,
            created_by=self.owner,
            entity_type=SpreadsheetImport.EntityType.COMMITMENT,
            file_name="origem.csv",
            content_sha256="a" * 64,
            source_data={"CSV": {"headers": ["number"], "rows": []}},
        )
        ImportEvent.objects.create(
            spreadsheet_import=spreadsheet_import,
            contract=self.contract,
            actor=self.owner,
            event_type=ImportEvent.EventType.UPLOADED,
            details={"arquivo": "origem.csv"},
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.contract_url())
        self.assertContains(response, "Planilha enviada")
        self.assertContains(response, "origem.csv")

    def test_contract_audit_includes_csv_export_events(self):
        CsvExportEvent.objects.create(
            contract=self.contract,
            actor=self.owner,
            details={"arquivo": "contrato.csv", "linhas": 12},
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.contract_url(categoria="EXPORTACAO"))
        self.assertContains(response, "CSV gerado")
        self.assertContains(response, "contrato.csv")

    def test_filters_category_and_actor_on_server(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.contract_url(categoria="OS", usuario="Responsável"))
        self.assertContains(response, "OS criada")
        self.assertNotContains(response, "Contrato criado")
        response = self.client.get(self.contract_url(usuario="inexistente"))
        self.assertContains(response, "Nenhum evento encontrado")

    def test_sensitive_keys_are_masked_before_rendering(self):
        ContractEvent.objects.create(
            event_type=ContractEvent.EventType.UPDATED,
            contract=self.contract,
            actor=self.owner,
            details={"anterior": {"senha": "nao-exibir"}, "atual": {"token_api": "secreto", "objeto": "visível"}},
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.contract_url())
        self.assertContains(response, "[PROTEGIDO]", count=2)
        self.assertContains(response, "visível")
        self.assertNotContains(response, "nao-exibir")
        self.assertNotContains(response, "secreto")

    def test_document_upload_and_download_are_audited(self):
        document = self.create_document()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), PDF_CONTENT)
        self.assertEqual(
            list(DocumentEvent.objects.values_list("event_type", flat=True)),
            [DocumentEvent.EventType.DOWNLOADED, DocumentEvent.EventType.UPLOADED],
        )
        response = self.client.get(self.contract_url(categoria="DOCUMENTO"))
        self.assertContains(response, "Documento enviado")
        self.assertContains(response, "Documento baixado")

    def test_audit_rows_cannot_be_updated_or_deleted_in_database(self):
        event = ContractEvent.objects.filter(contract=self.contract).first()
        with self.assertRaises(DatabaseError), transaction.atomic():
            ContractEvent.objects.filter(pk=event.pk).update(details={"violado": True})
        with self.assertRaises(DatabaseError), transaction.atomic():
            ContractEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(ContractEvent.objects.filter(pk=event.pk).exists())

    def test_pagination_is_stable_and_limited_to_twenty_five(self):
        ContractEvent.objects.bulk_create(
            [
                ContractEvent(
                    event_type=ContractEvent.EventType.UPDATED,
                    contract=self.contract,
                    actor=self.owner,
                    details={"sequencia": number},
                )
                for number in range(30)
            ]
        )
        self.client.force_login(self.owner)
        first = self.client.get(self.contract_url())
        second = self.client.get(self.contract_url(pagina=2))
        self.assertEqual(len(first.context["audit_page"].object_list), 25)
        self.assertGreater(len(second.context["audit_page"].object_list), 0)
        first_ids = {entry.source_id for entry in first.context["audit_page"]}
        second_ids = {entry.source_id for entry in second.context["audit_page"]}
        self.assertFalse(first_ids & second_ids)
