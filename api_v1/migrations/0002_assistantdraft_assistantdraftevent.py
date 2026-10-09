import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api_v1", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="apicredential", name="access_mode",
            field=models.CharField(choices=[("READ_ONLY", "Somente leitura"), ("CONTROLLED_DRAFT", "Leitura e rascunhos controlados")], default="READ_ONLY", max_length=30, verbose_name="modo de acesso"),
        ),
        migrations.CreateModel(
            name="AssistantDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("entity_type", models.CharField(choices=[("CONTRATO", "Contrato"), ("ITEM", "Item"), ("EMPENHO", "Empenho"), ("OS", "Ordem de Serviço"), ("RATEIO", "Rateio"), ("EXECUCAO", "Execução"), ("NF", "Nota Fiscal"), ("PAGAMENTO", "Pagamento")], max_length=20, verbose_name="tipo")),
                ("context", models.JSONField(default=dict, verbose_name="contexto")),
                ("payload", models.JSONField(default=dict, verbose_name="dados propostos")),
                ("evidence", models.JSONField(default=list, verbose_name="fontes e evidências")),
                ("source_summary", models.TextField(verbose_name="resumo da origem")),
                ("status", models.CharField(choices=[("PENDENTE", "Pendente de revisão"), ("CONFIRMADO", "Confirmado"), ("REJEITADO", "Rejeitado")], db_index=True, default="PENDENTE", max_length=20, verbose_name="status")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="revisado em")),
                ("rejection_reason", models.TextField(blank=True, verbose_name="motivo da rejeição")),
                ("target_model", models.CharField(blank=True, max_length=100, verbose_name="modelo gravado")),
                ("target_id", models.PositiveBigIntegerField(blank=True, null=True, verbose_name="registro gravado")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assistant_drafts", to="contracts.contract", verbose_name="contrato")),
                ("created_by_credential", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="drafts", to="api_v1.apicredential", verbose_name="credencial técnica")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assistant_drafts", to=settings.AUTH_USER_MODEL, verbose_name="usuário autorizador")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reviewed_assistant_drafts", to=settings.AUTH_USER_MODEL, verbose_name="revisado por")),
            ],
            options={"verbose_name": "rascunho assistido", "verbose_name_plural": "rascunhos assistidos", "ordering": ("-created_at", "-pk")},
        ),
        migrations.CreateModel(
            name="AssistantDraftEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("RASCUNHO_CRIADO", "Rascunho criado"), ("RASCUNHO_CONFIRMADO", "Rascunho confirmado"), ("RASCUNHO_REJEITADO", "Rascunho rejeitado"), ("VALIDACAO_FALHOU", "Confirmação recusada pela validação")], max_length=30, verbose_name="evento")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assistant_draft_events", to=settings.AUTH_USER_MODEL, verbose_name="autor")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="assistant_draft_events", to="contracts.contract", verbose_name="contrato")),
                ("draft", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="api_v1.assistantdraft", verbose_name="rascunho")),
            ],
            options={"verbose_name": "evento de rascunho assistido", "verbose_name_plural": "eventos de rascunhos assistidos", "ordering": ("-created_at", "-pk")},
        ),
    ]
