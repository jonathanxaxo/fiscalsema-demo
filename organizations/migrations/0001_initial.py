import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0003_fiscal_registration"),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="nome")),
                ("is_active", models.BooleanField(default=True, verbose_name="ativa")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criada em")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="atualizada em")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_organizations",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="criada por",
                    ),
                ),
            ],
            options={
                "verbose_name": "organização",
                "verbose_name_plural": "organizações",
                "ordering": ("name", "pk"),
                "permissions": [("manage_organizations", "Pode administrar organizações e setores")],
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        name="organizations_name_ci_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="Sector",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200, verbose_name="nome")),
                ("is_active", models.BooleanField(default=True, verbose_name="ativo")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="atualizado em")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_sectors",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="criado por",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sectors",
                        to="organizations.organization",
                        verbose_name="organização",
                    ),
                ),
            ],
            options={
                "verbose_name": "setor",
                "verbose_name_plural": "setores",
                "ordering": ("organization__name", "name", "pk"),
                "constraints": [
                    models.UniqueConstraint(
                        django.db.models.functions.text.Lower("name"),
                        models.F("organization"),
                        name="organizations_sector_name_org_ci_unique",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="OrganizationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("ORGANIZACAO_CRIADA", "Organização criada"),
                            ("ORGANIZACAO_ATUALIZADA", "Organização atualizada"),
                            ("ORGANIZACAO_INATIVADA", "Organização inativada"),
                            ("ORGANIZACAO_ATIVADA", "Organização ativada"),
                            ("SETOR_CRIADO", "Setor criado"),
                            ("SETOR_ATUALIZADO", "Setor atualizado"),
                            ("SETOR_INATIVADO", "Setor inativado"),
                            ("SETOR_ATIVADO", "Setor ativado"),
                            ("USUARIO_VINCULADO", "Usuário vinculado"),
                        ],
                        max_length=30,
                        verbose_name="evento",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="registrado em")),
                ("details", models.JSONField(blank=True, default=dict, verbose_name="detalhes")),
                (
                    "actor",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="organization_events_performed",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="autor",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="organizations.organization",
                        verbose_name="organização",
                    ),
                ),
                (
                    "sector",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="events",
                        to="organizations.sector",
                        verbose_name="setor",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="organization_assignment_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="usuário vinculado",
                    ),
                ),
            ],
            options={
                "verbose_name": "evento de organização",
                "verbose_name_plural": "eventos de organizações",
                "ordering": ("-created_at", "-pk"),
            },
        ),
    ]
