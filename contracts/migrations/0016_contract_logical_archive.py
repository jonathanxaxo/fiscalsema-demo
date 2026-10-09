import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contracts", "0015_contract_closure_fields_and_events"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="archived_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="arquivado logicamente em",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="contracts_archived",
                to=settings.AUTH_USER_MODEL,
                verbose_name="arquivado logicamente por",
            ),
        ),
        migrations.AddField(
            model_name="contract",
            name="archive_reason",
            field=models.TextField(blank=True, verbose_name="justificativa do arquivamento"),
        ),
        migrations.AddConstraint(
            model_name="contract",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                        archive_reason="",
                    )
                    | (
                        models.Q(archived_at__isnull=False, archived_by__isnull=False)
                        & ~models.Q(archive_reason="")
                    )
                ),
                name="contracts_archive_consistent",
            ),
        ),
        migrations.AlterField(
            model_name="contractevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("CONTRATO_CRIADO", "Contrato criado"),
                    ("CONTRATO_ATUALIZADO", "Contrato atualizado"),
                    ("STATUS_ALTERADO", "Status alterado"),
                    ("CONTRATO_ENCERRADO", "Contrato encerrado"),
                    ("FISCAL_TRANSFERIDO", "Fiscal responsável transferido"),
                    ("CONTRATO_ARQUIVADO", "Contrato arquivado logicamente"),
                    ("CONTRATO_RESTAURADO", "Contrato restaurado"),
                ],
                max_length=30,
                verbose_name="evento",
            ),
        ),
    ]
