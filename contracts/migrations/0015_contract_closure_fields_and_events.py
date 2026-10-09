import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contracts", "0014_fiscalsubstitution_fiscalsubstitutionevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="contract",
            name="closed_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="encerrado em"),
        ),
        migrations.AddField(
            model_name="contract",
            name="closed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="contracts_closed", to=settings.AUTH_USER_MODEL, verbose_name="encerrado por"),
        ),
        migrations.AddField(
            model_name="contract",
            name="closure_reason",
            field=models.TextField(blank=True, verbose_name="justificativa do encerramento"),
        ),
        migrations.AlterField(
            model_name="contractevent",
            name="event_type",
            field=models.CharField(choices=[("CONTRATO_CRIADO", "Contrato criado"), ("CONTRATO_ATUALIZADO", "Contrato atualizado"), ("STATUS_ALTERADO", "Status alterado"), ("CONTRATO_ENCERRADO", "Contrato encerrado"), ("FISCAL_TRANSFERIDO", "Fiscal responsável transferido")], max_length=30, verbose_name="evento"),
        ),
    ]
