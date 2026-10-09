import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("contracts", "0013_csvexportevent"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="ApiCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120, verbose_name="nome")),
                ("token_prefix", models.CharField(editable=False, max_length=16, unique=True, verbose_name="prefixo")),
                ("token_hash", models.CharField(editable=False, max_length=64, verbose_name="hash do token")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criada em")),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="expira em")),
                ("revoked_at", models.DateTimeField(blank=True, null=True, verbose_name="revogada em")),
                ("last_used_at", models.DateTimeField(blank=True, null=True, verbose_name="último uso")),
                ("rate_window_started_at", models.DateTimeField(blank=True, null=True, verbose_name="início da janela")),
                ("rate_window_count", models.PositiveIntegerField(default=0, verbose_name="requisições na janela")),
                ("authorized_user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="api_credentials", to=settings.AUTH_USER_MODEL, verbose_name="usuário autorizador")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_api_credentials", to=settings.AUTH_USER_MODEL, verbose_name="criada por")),
                ("revoked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="revoked_api_credentials", to=settings.AUTH_USER_MODEL, verbose_name="revogada por")),
            ],
            options={"verbose_name": "credencial da API", "verbose_name_plural": "credenciais da API", "ordering": ("name", "pk")},
        ),
        migrations.CreateModel(
            name="ApiAccessEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("CONSULTA", "Consulta autorizada"), ("NEGADA", "Consulta negada")], max_length=20, verbose_name="evento")),
                ("endpoint", models.CharField(max_length=255, verbose_name="endpoint")),
                ("method", models.CharField(max_length=10, verbose_name="método")),
                ("status_code", models.PositiveSmallIntegerField(verbose_name="status HTTP")),
                ("result_count", models.PositiveIntegerField(default=0, verbose_name="quantidade de resultados")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="api_access_events", to=settings.AUTH_USER_MODEL, verbose_name="usuário autorizador")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="api_access_events", to="contracts.contract", verbose_name="contrato")),
                ("credential", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="events", to="api_v1.apicredential", verbose_name="credencial")),
            ],
            options={"verbose_name": "evento de acesso à API", "verbose_name_plural": "eventos de acesso à API", "ordering": ("-created_at", "-pk")},
        ),
    ]
