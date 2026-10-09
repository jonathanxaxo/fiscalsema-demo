import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0011_alter_contractsharingevent_event_type"),
        ("documents", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("DOCUMENTO_ENVIADO", "Documento enviado"), ("DOCUMENTO_BAIXADO", "Documento baixado")], max_length=30, verbose_name="evento")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="document_events_performed", to=settings.AUTH_USER_MODEL, verbose_name="autor")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="document_events", to="contracts.contract", verbose_name="contrato")),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="documents.document", verbose_name="documento")),
            ],
            options={
                "verbose_name": "evento de documento",
                "verbose_name_plural": "eventos de documentos",
                "ordering": ("-created_at", "-pk"),
            },
        ),
    ]
