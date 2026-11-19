from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contracts", "0023_nf_servicos_devolucao")]

    operations = [
        migrations.AlterField(
            model_name="contractaccess",
            name="access_type",
            field=models.CharField(
                choices=[
                    ("READ_ONLY", "Somente leitura"),
                    ("GESTOR_CONTRATO", "Gestor do Contrato"),
                ],
                default="READ_ONLY",
                max_length=20,
                verbose_name="tipo de acesso",
            ),
        ),
        migrations.AlterField(
            model_name="contractinvitation",
            name="access_type",
            field=models.CharField(
                choices=[
                    ("READ_ONLY", "Somente leitura"),
                    ("GESTOR_CONTRATO", "Gestor do Contrato"),
                ],
                default="READ_ONLY",
                max_length=20,
                verbose_name="tipo de acesso",
            ),
        ),
    ]
