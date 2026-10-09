from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contracts", "0011_alter_contractsharingevent_event_type")]

    operations = [
        migrations.AlterField(
            model_name="workorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("RASCUNHO", "Rascunho"),
                    ("ABERTA", "Aberta"),
                    ("ASSINADA", "Assinada"),
                    ("EM_EXECUCAO", "Em execução"),
                    ("CONCLUIDA", "Concluída"),
                    ("HISTORICO_IMPORTADO", "Histórico importado"),
                    ("CANCELADA", "Cancelada"),
                    ("SUSPENSA", "Suspensa"),
                ],
                db_index=True,
                default="RASCUNHO",
                max_length=20,
                verbose_name="status",
            ),
        ),
    ]
