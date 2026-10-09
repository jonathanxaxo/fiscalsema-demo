from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0006_user_lifecycle")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="profile",
            field=models.CharField(
                choices=[
                    ("ADMINISTRADOR", "Administrador"),
                    ("FISCAL", "Fiscal"),
                    ("USUARIO_CONSULTA", "Usuário de Consulta"),
                ],
                default="FISCAL",
                max_length=20,
                verbose_name="perfil",
            ),
        ),
    ]
