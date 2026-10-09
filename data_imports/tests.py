import io
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, transaction
from django.urls import reverse
from openpyxl import Workbook

from contracts.models import BudgetCommitment, Invoice, WorkOrder, WorkOrderStatus
from contracts.services import share_contract_read_only
from contracts.test_work_orders import WorkOrderBase

from .models import ImportEvent, SpreadsheetImport
from .services import build_preview, confirm_import, create_import, parse_spreadsheet


def csv_upload(name, text):
    return SimpleUploadedFile(name, text.encode("utf-8"), content_type="text/csv")


def canonical_mapping(entity_type):
    from .services import ENTITY_FIELDS
    return {field["name"]: field["name"] for field in ENTITY_FIELDS[entity_type]}


class SpreadsheetImportTests(WorkOrderBase):
    def commitment_file(self, *, number="2026NE0001", value="1.234,56"):
        return csv_upload(
            "empenhos.csv",
            "number;ped;commitment_date;initial_value;source;notes;is_active\n"
            f"{number};2026PED001;30/09/2026;{value};Fonte 100;Migração;Sim\n",
        )

    def create_job(self, entity_type, uploaded):
        return create_import(
            contract=self.contract, actor=self.owner,
            entity_type=entity_type, uploaded=uploaded,
        )

    def preview(self, job):
        return build_preview(
            spreadsheet_import=job, actor=self.owner, sheet="CSV",
            mapping=canonical_mapping(job.entity_type),
        )

    def test_csv_upload_identifies_headers_hash_and_audits_without_operational_write(self):
        job = self.create_job(SpreadsheetImport.EntityType.COMMITMENT, self.commitment_file())
        self.assertEqual(job.source_data["CSV"]["headers"][0], "number")
        self.assertEqual(len(job.content_sha256), 64)
        self.assertEqual(BudgetCommitment.objects.count(), 0)
        self.assertTrue(job.events.filter(event_type=ImportEvent.EventType.UPLOADED).exists())

    def test_xlsx_identifies_multiple_sheets_and_rejects_formulas(self):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Empenhos"
        worksheet.append(["number", "ped"])
        worksheet.append(["2026NE1", "2026PED1"])
        second = workbook.create_sheet("Notas")
        second.append(["number"])
        second.append(["NF1"])
        buffer = io.BytesIO()
        workbook.save(buffer)
        uploaded = SimpleUploadedFile("dados.xlsx", buffer.getvalue())
        _, source = parse_spreadsheet(uploaded)
        self.assertEqual(set(source), {"Empenhos", "Notas"})

        job = self.create_job(
            SpreadsheetImport.EntityType.COMMITMENT,
            SimpleUploadedFile("multiplas.xlsx", buffer.getvalue()),
        )
        self.client.force_login(self.owner)
        response = self.client.get(
            reverse("data_imports:mapping", args=[self.contract.pk, job.pk]),
            {"sheet": "Notas"},
        )
        self.assertEqual(response.context["form"].initial["sheet"], "Notas")
        self.assertEqual(response.context["form"].fields["field_number"].choices[1][0], "number")

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.append(["number", "value"])
        worksheet.append(["A", "=1+1"])
        buffer = io.BytesIO()
        workbook.save(buffer)
        with self.assertRaisesMessage(ValidationError, "contém fórmula"):
            parse_spreadsheet(SimpleUploadedFile("formula.xlsx", buffer.getvalue()))

    def test_preview_normalizes_and_validates_without_writing_then_confirmation_imports(self):
        job = self.create_job(SpreadsheetImport.EntityType.COMMITMENT, self.commitment_file())
        self.preview(job)
        job.refresh_from_db()
        self.assertEqual((job.valid_rows, job.error_rows, job.duplicate_rows), (1, 0, 0))
        self.assertEqual(BudgetCommitment.objects.count(), 0)
        self.assertTrue(job.events.filter(event_type=ImportEvent.EventType.PREVIEWED).exists())

        confirm_import(spreadsheet_import_id=job.pk, actor=self.owner)
        commitment = BudgetCommitment.objects.get()
        self.assertEqual(commitment.initial_value, Decimal("1234.56"))
        job.refresh_from_db()
        self.assertEqual(job.status, SpreadsheetImport.Status.COMPLETED)
        self.assertEqual(job.report["importados"], 1)
        self.assertTrue(job.events.filter(event_type=ImportEvent.EventType.COMPLETED).exists())

    def test_errors_block_confirmation_and_keep_database_unchanged(self):
        job = self.create_job(
            SpreadsheetImport.EntityType.COMMITMENT,
            self.commitment_file(value="valor-invalido"),
        )
        self.preview(job)
        job.refresh_from_db()
        self.assertEqual(job.error_rows, 1)
        self.assertIn("número inválido", job.preview[0]["errors"][0])
        with self.assertRaisesMessage(ValidationError, "Corrija todas"):
            confirm_import(spreadsheet_import_id=job.pk, actor=self.owner)
        self.assertEqual(BudgetCommitment.objects.count(), 0)

    def test_existing_and_in_file_duplicates_are_reported_and_never_overwritten(self):
        first = self.create_job(SpreadsheetImport.EntityType.COMMITMENT, self.commitment_file())
        self.preview(first)
        confirm_import(spreadsheet_import_id=first.pk, actor=self.owner)
        original = BudgetCommitment.objects.get()
        content = (
            "number;ped;commitment_date;initial_value;source;notes;is_active\n"
            "2026NE0001;2026PED001;30/09/2026;9999,99;Outra;X;Sim\n"
            "2026NE0002;2026PED002;30/09/2026;100,00;Fonte;X;Sim\n"
            "2026NE0002;2026PED002;30/09/2026;200,00;Fonte;X;Sim\n"
        )
        second = self.create_job(
            SpreadsheetImport.EntityType.COMMITMENT, csv_upload("outro.csv", content)
        )
        self.preview(second)
        second.refresh_from_db()
        self.assertEqual((second.valid_rows, second.duplicate_rows), (1, 2))
        confirm_import(spreadsheet_import_id=second.pk, actor=self.owner)
        original.refresh_from_db()
        self.assertEqual(original.initial_value, Decimal("1234.56"))
        self.assertEqual(BudgetCommitment.objects.count(), 2)

    def test_same_completed_file_is_idempotently_rejected(self):
        content = self.commitment_file().read()
        first = self.create_job(
            SpreadsheetImport.EntityType.COMMITMENT,
            SimpleUploadedFile("empenhos.csv", content),
        )
        self.preview(first)
        confirm_import(spreadsheet_import_id=first.pk, actor=self.owner)
        with self.assertRaisesMessage(ValidationError, "já foi importado"):
            self.create_job(
                SpreadsheetImport.EntityType.COMMITMENT,
                SimpleUploadedFile("copia.csv", content),
            )

    def test_work_order_import_resolves_item_and_accepts_historical_status(self):
        content = (
            "number;item_number;description;quantity;hours;responsible;opening_date;signature_date;start_date;deadline;completion_date;status;process_number;notes\n"
            "OS-HIST-1;1;Histórico;;10;Fiscal confirmado;01/09/2026;;;;;HISTORICO_IMPORTADO;PROC-HIST;Origem legada\n"
        )
        job = self.create_job(SpreadsheetImport.EntityType.WORK_ORDER, csv_upload("os.csv", content))
        self.preview(job)
        job.refresh_from_db()
        self.assertEqual(job.error_rows, 0)
        self.assertEqual(WorkOrder.objects.count(), 0)
        confirm_import(spreadsheet_import_id=job.pk, actor=self.owner)
        order = WorkOrder.objects.get()
        self.assertEqual(order.item, self.item)
        self.assertEqual(order.status, WorkOrderStatus.HISTORICAL_IMPORTED)

    def test_invoice_import_resolves_work_order_and_reuses_financial_validation(self):
        order = self.create_work_order(hours=Decimal("40.0000"), status=WorkOrderStatus.IN_PROGRESS)
        content = (
            "work_order_number;number;series;supplier_name;supplier_tax_id;issue_date;competence;gross_value;deduction_value;accepted_value;process_number;status;document_reference;document_hash;notes\n"
            f"{order.number};NF-IMPORT;A;{self.contract.supplier_name};{self.contract.supplier_tax_id};30/09/2026;09/2026;1000,00;0;1000,00;PROC-NF;Recebida;;;Legado\n"
        )
        job = self.create_job(SpreadsheetImport.EntityType.INVOICE, csv_upload("nf.csv", content))
        self.preview(job)
        job.refresh_from_db()
        self.assertEqual(job.error_rows, 0)
        self.assertEqual(Invoice.objects.count(), 0)
        confirm_import(spreadsheet_import_id=job.pk, actor=self.owner)
        self.assertEqual(Invoice.objects.get().work_order, order)

    def test_read_only_foreign_and_anonymous_users_cannot_access_import(self):
        upload_url = reverse("data_imports:upload", args=[self.contract.pk])
        self.assertEqual(self.client.get(upload_url).status_code, 302)
        share_contract_read_only(
            contract_id=self.contract.pk, actor=self.owner, email=self.other.email,
        )
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(upload_url).status_code, 404)

    def test_import_owner_cannot_cross_contract_or_actor_scope(self):
        job = self.create_job(SpreadsheetImport.EntityType.COMMITMENT, self.commitment_file())
        self.client.force_login(self.other)
        detail = reverse("data_imports:detail", args=[self.contract.pk, job.pk])
        self.assertEqual(self.client.get(detail).status_code, 404)

    def test_web_flow_shows_mapping_preview_and_requires_post_to_confirm(self):
        self.client.force_login(self.owner)
        upload_url = reverse("data_imports:upload", args=[self.contract.pk])
        response = self.client.post(upload_url, {
            "entity_type": SpreadsheetImport.EntityType.COMMITMENT,
            "file": self.commitment_file(),
        })
        job = SpreadsheetImport.objects.get()
        self.assertRedirects(response, reverse("data_imports:mapping", args=[self.contract.pk, job.pk]))
        mapping_url = reverse("data_imports:mapping", args=[self.contract.pk, job.pk])
        data = {"sheet": "CSV", **{f"field_{key}": value for key, value in canonical_mapping(job.entity_type).items()}}
        response = self.client.post(mapping_url, data)
        self.assertRedirects(response, reverse("data_imports:detail", args=[self.contract.pk, job.pk]))
        detail = self.client.get(reverse("data_imports:detail", args=[self.contract.pk, job.pk]))
        self.assertContains(detail, "Nenhum dado é gravado", count=0)
        self.assertContains(detail, "Confirmar importação")
        confirm_url = reverse("data_imports:confirm", args=[self.contract.pk, job.pk])
        self.assertEqual(self.client.get(confirm_url).status_code, 405)
        self.assertEqual(BudgetCommitment.objects.count(), 0)

    def test_import_audit_event_is_immutable_in_postgresql(self):
        job = self.create_job(SpreadsheetImport.EntityType.COMMITMENT, self.commitment_file())
        event = job.events.get()
        with self.assertRaises(DatabaseError), transaction.atomic():
            ImportEvent.objects.filter(pk=event.pk).delete()
        self.assertTrue(ImportEvent.objects.filter(pk=event.pk).exists())
