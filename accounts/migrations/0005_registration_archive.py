import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_user_organization_sector")]

    operations = [
        migrations.AddField(
            model_name="registrationrequest",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="arquivada em"),
        ),
        migrations.AddField(
            model_name="registrationrequest",
            name="archived_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="archived_registration_requests",
                to="accounts.user",
                verbose_name="arquivada por",
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
                ],
                max_length=30,
            ),
        ),
    ]
