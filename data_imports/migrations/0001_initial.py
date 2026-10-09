import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("contracts", "0012_alter_workorder_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="SpreadsheetImport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(choices=[("EMPENHO", "Empenhos"), ("OS", "Ordens de Serviço"), ("NF", "Notas Fiscais")], max_length=20, verbose_name="tipo")),
                ("status", models.CharField(choices=[("ENVIADO", "Arquivo enviado"), ("PREVIA", "Prévia validada"), ("CONCLUIDO", "Importação concluída"), ("FALHOU", "Falha na confirmação")], default="ENVIADO", max_length=20, verbose_name="situação")),
                ("file_name", models.CharField(max_length=255, verbose_name="arquivo de origem")),
                ("content_sha256", models.CharField(db_index=True, max_length=64, verbose_name="SHA-256")),
                ("source_data", models.JSONField(default=dict, verbose_name="dados identificados")),
                ("selected_sheet", models.CharField(blank=True, max_length=100, verbose_name="aba selecionada")),
                ("mapping", models.JSONField(blank=True, default=dict, verbose_name="mapeamento")),
                ("preview", models.JSONField(blank=True, default=list, verbose_name="prévia")),
                ("report", models.JSONField(blank=True, default=dict, verbose_name="relatório")),
                ("total_rows", models.PositiveIntegerField(default=0, verbose_name="linhas encontradas")),
                ("valid_rows", models.PositiveIntegerField(default=0, verbose_name="linhas válidas")),
                ("duplicate_rows", models.PositiveIntegerField(default=0, verbose_name="duplicidades")),
                ("error_rows", models.PositiveIntegerField(default=0, verbose_name="linhas com erro")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="criada em")),
                ("confirmed_at", models.DateTimeField(blank=True, null=True, verbose_name="confirmada em")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="spreadsheet_imports", to="contracts.contract", verbose_name="contrato")),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="spreadsheet_imports", to=settings.AUTH_USER_MODEL, verbose_name="usuário")),
            ],
            options={"verbose_name": "importação de planilha", "verbose_name_plural": "importações de planilhas", "ordering": ("-created_at", "-pk")},
        ),
        migrations.CreateModel(
            name="ImportEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("IMPORTACAO_ENVIADA", "Planilha enviada"), ("IMPORTACAO_VALIDADA", "Prévia de importação validada"), ("IMPORTACAO_CONFIRMADA", "Importação confirmada"), ("IMPORTACAO_FALHOU", "Importação não concluída")], max_length=40, verbose_name="evento")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="import_events_performed", to=settings.AUTH_USER_MODEL, verbose_name="autor")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="import_events", to="contracts.contract", verbose_name="contrato")),
                ("spreadsheet_import", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="data_imports.spreadsheetimport", verbose_name="importação")),
            ],
            options={"verbose_name": "evento de importação", "verbose_name_plural": "eventos de importação", "ordering": ("-created_at", "-pk")},
        ),
        migrations.AddConstraint(
            model_name="spreadsheetimport",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "CONCLUIDO")), fields=("contract", "entity_type", "content_sha256"), name="data_import_completed_file_unique"),
        ),
    ]
