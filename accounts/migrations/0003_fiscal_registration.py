import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_access_groups_and_admin_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="organization_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="organização informada"),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(blank=True, max_length=30, verbose_name="telefone"),
        ),
        migrations.AddField(
            model_name="user",
            name="sector_name",
            field=models.CharField(blank=True, max_length=200, verbose_name="setor informado"),
        ),
        migrations.AlterField(
            model_name="authenticationevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("LOGIN_SUCESSO", "Login realizado"),
                    ("LOGIN_FALHA", "Falha de login"),
                    ("LOGOUT", "Logout realizado"),
                    ("SENHA_ALTERADA", "Senha alterada"),
                    ("ADMIN_CRIADO", "Administrador inicial criado"),
                    ("CADASTRO_SOLICITADO", "Cadastro solicitado"),
                    ("CADASTRO_APROVADO", "Cadastro aprovado"),
                    ("CADASTRO_REJEITADO", "Cadastro rejeitado"),
                    ("FISCAL_CRIADO", "Fiscal criado pelo Administrador"),
                ],
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="RegistrationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDENTE", "Pendente"),
                            ("APROVADO", "Aprovado"),
                            ("REJEITADO", "Rejeitado"),
                        ],
                        default="PENDENTE",
                        max_length=20,
                        verbose_name="status",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="solicitado em")),
                ("reviewed_at", models.DateTimeField(blank=True, null=True, verbose_name="analisado em")),
                ("rejection_reason", models.TextField(blank=True, verbose_name="motivo da rejeição")),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewed_registration_requests",
                        to="accounts.user",
                        verbose_name="analisado por",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="registration_request",
                        to="accounts.user",
                        verbose_name="usuário",
                    ),
                ),
            ],
            options={
                "verbose_name": "solicitação de cadastro",
                "verbose_name_plural": "solicitações de cadastro",
                "ordering": ("-created_at", "-pk"),
                "constraints": [
                    models.CheckConstraint(
                        condition=(
                            models.Q(
                                ("rejection_reason", ""),
                                ("reviewed_at__isnull", True),
                                ("reviewed_by__isnull", True),
                                ("status", "PENDENTE"),
                            )
                            | models.Q(
                                ("rejection_reason", ""),
                                ("reviewed_at__isnull", False),
                                ("reviewed_by__isnull", False),
                                ("status", "APROVADO"),
                            )
                            | (
                                models.Q(
                                    ("reviewed_at__isnull", False),
                                    ("reviewed_by__isnull", False),
                                    ("status", "REJEITADO"),
                                )
                                & ~models.Q(("rejection_reason", ""))
                            )
                        ),
                        name="accounts_registration_review_state_valid",
                    )
                ],
            },
        ),
    ]
