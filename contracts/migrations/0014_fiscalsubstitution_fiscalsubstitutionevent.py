import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contracts", "0013_csvexportevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiscalSubstitution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254, verbose_name="e-mail do substituto")),
                ("starts_on", models.DateField(db_index=True, verbose_name="início da substituição")),
                ("ends_on", models.DateField(db_index=True, verbose_name="fim da substituição")),
                ("status", models.CharField(choices=[("PENDENTE_CONTA", "Aguardando conta aprovada"), ("VINCULADO", "Vinculado"), ("REVOGADO", "Revogado")], db_index=True, default="PENDENTE_CONTA", max_length=20, verbose_name="status")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("linked_at", models.DateTimeField(blank=True, null=True, verbose_name="vinculado em")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="revogado em")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_substitutions", to="contracts.contract", verbose_name="contrato")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_substitutions_created", to=settings.AUTH_USER_MODEL, verbose_name="criado por")),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_substitutions_revoked", to=settings.AUTH_USER_MODEL, verbose_name="revogado por")),
                ("substitute", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_substitutions", to=settings.AUTH_USER_MODEL, verbose_name="Fiscal substituto")),
            ],
            options={
                "verbose_name": "substituição de Fiscal",
                "verbose_name_plural": "substituições de Fiscal",
                "ordering": ("-starts_on", "-created_at", "pk"),
            },
        ),
        migrations.CreateModel(
            name="FiscalSubstitutionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("SUBSTITUICAO_CRIADA", "Substituição criada"), ("SUBSTITUICAO_VINCULADA", "Substituição vinculada"), ("SUBSTITUICAO_REVOGADA", "Substituição revogada")], max_length=30, verbose_name="evento")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="fiscal_substitution_events_performed", to=settings.AUTH_USER_MODEL, verbose_name="autor")),
                ("contract", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fiscal_substitution_events", to="contracts.contract", verbose_name="contrato")),
                ("substitution", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="contracts.fiscalsubstitution", verbose_name="substituição")),
            ],
            options={
                "verbose_name": "evento de substituição de Fiscal",
                "verbose_name_plural": "eventos de substituição de Fiscal",
                "ordering": ("-created_at", "-pk"),
            },
        ),
        migrations.AddConstraint(
            model_name="fiscalsubstitution",
            constraint=models.CheckConstraint(
                condition=models.Q(("ends_on__gte", models.F("starts_on"))),
                name="contracts_substitution_period_order",
            ),
        ),
    ]
