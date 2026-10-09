import uuid

from django.db import migrations, models


def assign_unique_legacy_batches(apps, schema_editor):
    draft_model = apps.get_model("api_v1", "AssistantDraft")
    for draft in draft_model.objects.only("pk").iterator():
        draft_model.objects.filter(pk=draft.pk).update(batch_id=uuid.uuid4())


class Migration(migrations.Migration):
    dependencies = [("api_v1", "0002_assistantdraft_assistantdraftevent")]

    operations = [
        migrations.AddField(
            model_name="assistantdraft",
            name="operation",
            field=models.CharField(
                choices=[("CRIAR", "Criar registro"), ("ATUALIZAR", "Atualizar registro existente")],
                default="CRIAR", max_length=20, verbose_name="operação",
            ),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="batch_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, verbose_name="lote"),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="source_authority",
            field=models.CharField(
                choices=[
                    ("SISTEMA_HOMOLOGADO", "Dado homologado no sistema"),
                    ("DOCUMENTO_OFICIAL_VALIDADO", "Documento oficial validado"),
                    ("IMPORTACAO_CONFIRMADA", "Importação confirmada"),
                    ("EXTRACAO_AUTOMATICA", "Extração automática da IA"),
                ],
                default="EXTRACAO_AUTOMATICA", max_length=40,
                verbose_name="autoridade da fonte",
            ),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="confidence_level",
            field=models.CharField(
                choices=[
                    ("CONFIRMADO", "Confirmado"),
                    ("ENCONTRADO_EM_FONTE", "Encontrado em fonte"),
                    ("CALCULADO_PELO_SISTEMA", "Calculado pelo sistema"),
                    ("INFERIDO", "Inferido"),
                    ("ESTIMADO", "Estimado"),
                    ("PENDENTE", "Pendente"),
                    ("DIVERGENTE", "Divergente"),
                ],
                default="ENCONTRADO_EM_FONTE", max_length=30,
                verbose_name="nível de confiança",
            ),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="comparison",
            field=models.JSONField(blank=True, default=list, verbose_name="comparação com o sistema"),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="consistency_result",
            field=models.JSONField(blank=True, default=dict, verbose_name="resultado da consistência"),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="baseline_hash",
            field=models.CharField(blank=True, editable=False, max_length=64, verbose_name="hash do estado comparado"),
        ),
        migrations.AddField(
            model_name="assistantdraft", name="requires_human_confirmation",
            field=models.BooleanField(default=True, editable=False, verbose_name="exige confirmação humana"),
        ),
        migrations.RunPython(assign_unique_legacy_batches, migrations.RunPython.noop),
    ]
