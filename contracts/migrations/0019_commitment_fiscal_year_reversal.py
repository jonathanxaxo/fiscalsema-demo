from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0018_contractitem_annual_controls"),
    ]

    operations = [
        migrations.AddField(
            model_name="budgetcommitment",
            name="closed_for_new_allocations_at",
            field=models.DateField(
                blank=True,
                help_text=(
                    "Preenchido automaticamente após o estorno do saldo do exercício."
                ),
                null=True,
                verbose_name="encerrado para novos rateios em",
            ),
        ),
        migrations.AddField(
            model_name="commitmentmovement",
            name="document_reference",
            field=models.CharField(
                blank=True,
                help_text="Obrigatória para estorno do saldo do exercício.",
                max_length=255,
                verbose_name="referência do documento oficial",
            ),
        ),
        migrations.AlterField(
            model_name="commitmentmovement",
            name="movement_type",
            field=models.CharField(
                choices=[
                    ("REFORCO", "Reforço"),
                    ("ANULACAO", "Anulação"),
                    ("ESTORNO", "Estorno do saldo do exercício"),
                ],
                max_length=10,
                verbose_name="tipo",
            ),
        ),
    ]
