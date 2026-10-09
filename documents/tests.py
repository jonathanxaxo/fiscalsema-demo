import hashlib
import shutil
import tempfile

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from contracts.models import WorkOrderStatus
from contracts.services import share_contract_read_only
from contracts.test_work_orders import WorkOrderBase

from .models import Document, DocumentType, RelatedEntityType
from .services import create_document


PDF_CONTENT = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def pdf_upload(name="contrato.pdf", content=PDF_CONTENT, content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


class DocumentTests(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.order = self.create_work_order(status=WorkOrderStatus.IN_PROGRESS)
        self.media_directory = tempfile.mkdtemp(prefix="fiscalsema-documents-")
        self.settings_override = override_settings(
            MEDIA_ROOT=self.media_directory,
            DOCUMENT_MAX_UPLOAD_SIZE=20 * 1024 * 1024,
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.media_directory, True)

    def data(self, **overrides):
        data = {
            "title": "Contrato assinado",
            "document_type": DocumentType.CONTRACT,
            "origin": "SIGADOC",
            "related_entity_type": RelatedEntityType.CONTRACT,
            "item": None,
            "commitment": None,
            "work_order": None,
            "execution": None,
            "invoice": None,
            "payment": None,
            "previous_version": None,
        }
        data.update(overrides)
        return data

    def create_pdf(self, **overrides):
        file = overrides.pop("file", pdf_upload())
        return create_document(
            contract_id=self.contract.pk, actor=self.owner, file=file,
            **self.data(**overrides),
        )

    def test_upload_records_metadata_hash_owner_and_private_path(self):
        document = self.create_pdf()
        self.assertEqual(document.sha256, hashlib.sha256(PDF_CONTENT).hexdigest())
        self.assertEqual(document.uploaded_by, self.owner)
        self.assertEqual(document.file_size, len(PDF_CONTENT))
        self.assertTrue(document.file.name.startswith(f"contratos/{self.contract.pk}/"))
        self.assertNotIn("contrato.pdf", document.file.name)

    def test_owner_lists_and_downloads_through_authorized_stream(self):
        document = self.create_pdf()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("documents:list", args=[self.contract.pk]))
        self.assertContains(response, "Contrato assinado")
        response = self.client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(response.streaming_content), PDF_CONTENT)

    def test_upload_form_accepts_entity_from_same_contract(self):
        self.client.force_login(self.owner)
        response = self.client.post(
            reverse("documents:upload", args=[self.contract.pk]),
            {
                "title": "OS assinada",
                "document_type": DocumentType.WORK_ORDER,
                "origin": "SIGADOC",
                "related_entity_type": RelatedEntityType.WORK_ORDER,
                "work_order": self.order.pk,
                "file": pdf_upload("os-assinada.pdf"),
            },
        )
        self.assertRedirects(response, reverse("documents:list", args=[self.contract.pk]))
        document = Document.objects.get(title="OS assinada")
        self.assertEqual(document.work_order, self.order)
        self.assertEqual(document.contract, self.contract)

    def test_read_only_user_can_list_and_download_but_cannot_upload(self):
        document = self.create_pdf()
        share_contract_read_only(
            contract_id=self.contract.pk, actor=self.owner, email=self.other.email
        )
        self.client.force_login(self.other)
        self.assertContains(
            self.client.get(reverse("documents:list", args=[self.contract.pk])),
            "Contrato assinado",
        )
        self.assertEqual(
            self.client.get(reverse("documents:download", args=[document.pk])).status_code, 200
        )
        self.assertEqual(
            self.client.get(reverse("documents:upload", args=[self.contract.pk])).status_code, 403
        )

    def test_foreign_user_cannot_discover_contract_or_document(self):
        document = self.create_pdf()
        self.client.force_login(self.other)
        self.assertEqual(
            self.client.get(reverse("documents:list", args=[self.contract.pk])).status_code, 404
        )
        self.assertEqual(
            self.client.get(reverse("documents:download", args=[document.pk])).status_code, 404
        )

    def test_anonymous_access_requires_login(self):
        document = self.create_pdf()
        self.assertEqual(
            self.client.get(reverse("documents:list", args=[self.contract.pk])).status_code,
            302,
        )
        self.assertEqual(
            self.client.get(reverse("documents:download", args=[document.pk])).status_code,
            302,
        )
        self.assertEqual(
            self.client.get(reverse("documents:upload", args=[self.contract.pk])).status_code,
            403,
        )

    def test_extension_mime_and_signature_are_validated(self):
        invalid_files = (
            SimpleUploadedFile("malware.exe", b"MZ", content_type="application/octet-stream"),
            SimpleUploadedFile("falso.pdf", b"nao-e-pdf", content_type="application/pdf"),
            SimpleUploadedFile("falso.png", b"nao-e-png", content_type="image/png"),
            SimpleUploadedFile("falso.jpg", b"nao-e-jpeg", content_type="image/jpeg"),
            SimpleUploadedFile("falso.docx", b"nao-e-zip", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        )
        for uploaded in invalid_files:
            with self.subTest(name=uploaded.name), self.assertRaises(ValidationError):
                self.create_pdf(file=uploaded)
        self.assertEqual(Document.objects.count(), 0)

    @override_settings(DOCUMENT_MAX_UPLOAD_SIZE=10)
    def test_empty_and_oversized_files_are_rejected(self):
        for uploaded in (pdf_upload(content=b""), pdf_upload(content=PDF_CONTENT)):
            with self.assertRaises(ValidationError):
                self.create_pdf(file=uploaded)

    def test_related_entity_must_belong_to_same_contract(self):
        second = self.contract.__class__.objects.create(
            number="038/2026", process_number="P-2", object="Outro objeto",
            contracting_organization=self.organization, supplier_name="Fornecedor",
            supplier_tax_id="12345678000199", signature_date=self.contract.signature_date,
            validity_start=self.contract.validity_start, validity_end=self.contract.validity_end,
            original_value=self.contract.original_value, responsible_fiscal=self.owner,
        )
        foreign_item = self.item.__class__.objects.create(
            contract=second, number="X", description="Item externo", category="Categoria",
            unit=self.item.unit, contracted_quantity="1.0000", unit_value="1.00",
            created_by=self.owner,
        )
        with self.assertRaises(ValidationError):
            self.create_pdf(
                related_entity_type=RelatedEntityType.ITEM, item=foreign_item,
            )

    def test_new_version_preserves_previous_file_and_rejects_branch(self):
        first = self.create_pdf()
        second = self.create_pdf(previous_version=first, file=pdf_upload("contrato-v2.pdf", PDF_CONTENT + b"v2"))
        self.assertEqual(second.version, 2)
        self.assertEqual(second.previous_version, first)
        self.assertNotEqual(second.file.name, first.file.name)
        self.assertTrue(first.file.storage.exists(first.file.name))
        with self.assertRaisesMessage(ValidationError, "já possui uma sucessora"):
            self.create_pdf(previous_version=first, file=pdf_upload("contrato-v3.pdf", PDF_CONTENT + b"v3"))

    def test_version_cannot_silently_change_metadata(self):
        first = self.create_pdf()
        with self.assertRaisesMessage(ValidationError, "deve manter"):
            self.create_pdf(
                previous_version=first, title="Outro documento",
                file=pdf_upload("outro.pdf", PDF_CONTENT + b"novo"),
            )

    def test_saved_document_is_immutable_and_not_deletable(self):
        document = self.create_pdf()
        document.title = "Alterado"
        with self.assertRaisesMessage(ValidationError, "imutáveis"):
            document.save()
        with self.assertRaisesMessage(ValidationError, "não podem ser excluídos"):
            document.delete()

    def test_download_endpoint_rejects_post(self):
        document = self.create_pdf()
        self.client.force_login(self.owner)
        self.assertEqual(
            self.client.post(reverse("documents:download", args=[document.pk])).status_code,
            405,
        )
