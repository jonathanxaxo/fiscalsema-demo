from django.conf import settings
from django.db import models


class SpreadsheetImport(models.Model):
    class EntityType(models.TextChoices):
        COMMITMENT = "EMPENHO", "Empenhos"
        WORK_ORDER = "OS", "Ordens de Serviço"
        INVOICE = "NF", "Notas Fiscais"

    class Status(models.TextChoices):
        UPLOADED = "ENVIADO", "Arquivo enviado"
        PREVIEWED = "PREVIA", "Prévia validada"
        COMPLETED = "CONCLUIDO", "Importação concluída"
        FAILED = "FALHOU", "Falha na confirmação"

    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT,
        related_name="spreadsheet_imports", verbose_name="contrato",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="spreadsheet_imports", verbose_name="usuário",
    )
    entity_type = models.CharField("tipo", max_length=20, choices=EntityType.choices)
    status = models.CharField(
        "situação", max_length=20, choices=Status.choices, default=Status.UPLOADED,
    )
    file_name = models.CharField("arquivo de origem", max_length=255)
    content_sha256 = models.CharField("SHA-256", max_length=64, db_index=True)
    source_data = models.JSONField("dados identificados", default=dict)
    selected_sheet = models.CharField("aba selecionada", max_length=100, blank=True)
    mapping = models.JSONField("mapeamento", default=dict, blank=True)
    preview = models.JSONField("prévia", default=list, blank=True)
    report = models.JSONField("relatório", default=dict, blank=True)
    total_rows = models.PositiveIntegerField("linhas encontradas", default=0)
    valid_rows = models.PositiveIntegerField("linhas válidas", default=0)
    duplicate_rows = models.PositiveIntegerField("duplicidades", default=0)
    error_rows = models.PositiveIntegerField("linhas com erro", default=0)
    created_at = models.DateTimeField("criada em", auto_now_add=True, db_index=True)
    confirmed_at = models.DateTimeField("confirmada em", null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "importação de planilha"
        verbose_name_plural = "importações de planilhas"
        constraints = [
            models.UniqueConstraint(
                fields=("contract", "entity_type", "content_sha256"),
                condition=models.Q(status="CONCLUIDO"),
                name="data_import_completed_file_unique",
            ),
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()} — {self.file_name}"


class ImportEvent(models.Model):
    class EventType(models.TextChoices):
        UPLOADED = "IMPORTACAO_ENVIADA", "Planilha enviada"
        PREVIEWED = "IMPORTACAO_VALIDADA", "Prévia de importação validada"
        COMPLETED = "IMPORTACAO_CONFIRMADA", "Importação confirmada"
        FAILED = "IMPORTACAO_FALHOU", "Importação não concluída"

    spreadsheet_import = models.ForeignKey(
        SpreadsheetImport, on_delete=models.PROTECT,
        related_name="events", verbose_name="importação",
    )
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT,
        related_name="import_events", verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="import_events_performed", verbose_name="autor",
    )
    event_type = models.CharField("evento", max_length=40, choices=EventType.choices)
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de importação"
        verbose_name_plural = "eventos de importação"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.spreadsheet_import_id}"
