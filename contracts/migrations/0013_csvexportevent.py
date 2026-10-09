import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0012_alter_workorder_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CsvExportEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[("CSV_GERADO", "CSV gerado")],
                        default="CSV_GERADO", max_length=20, verbose_name="evento",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, db_index=True, verbose_name="registrado em",
                    ),
                ),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                (
                    "actor",
                    models.ForeignKey(
                        null=True, on_delete=django.db.models.deletion.SET_NULL,
                        related_name="csv_export_events_performed",
                        to=settings.AUTH_USER_MODEL, verbose_name="autor",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="csv_export_events", to="contracts.contract",
                        verbose_name="contrato",
                    ),
                ),
            ],
            options={
                "verbose_name": "evento de exportação CSV",
                "verbose_name_plural": "eventos de exportação CSV",
                "ordering": ("-created_at", "-pk"),
            },
        ),
    ]
