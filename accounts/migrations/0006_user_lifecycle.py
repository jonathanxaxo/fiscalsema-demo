import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0005_registration_archive")]

    operations = [
        migrations.AddField(
            model_name="user",
            name="archived_at",
            field=models.DateTimeField(
                blank=True,
                db_index=True,
                null=True,
                verbose_name="excluído logicamente em",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="archived_users",
                to="accounts.user",
                verbose_name="excluído logicamente por",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(("archived_at__isnull", True), ("archived_by__isnull", True))
                    | models.Q(("archived_at__isnull", False), ("archived_by__isnull", False))
                ),
                name="accounts_user_archive_consistent",
            ),
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
                    ("CADASTRO_ARQUIVADO", "Cadastro arquivado"),
                    ("FISCAL_CRIADO", "Fiscal criado pelo Administrador"),
                    ("CONTA_STATUS_ALTERADO", "Status da conta alterado"),
                    ("CONTA_ARQUIVADA", "Conta excluída logicamente"),
                    ("CONTA_RESTAURADA", "Conta restaurada"),
                ],
                max_length=30,
            ),
        ),
    ]
