from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0016_contract_logical_archive"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractitem",
            name="external_code",
            field=models.CharField(blank=True, max_length=30, verbose_name="código oficial"),
        ),
        migrations.AddField(
            model_name="contractitem",
            name="calculation_rule",
            field=models.TextField(blank=True, verbose_name="regra de cálculo"),
        ),
        migrations.AddField(
            model_name="contractitem",
            name="source_reference",
            field=models.TextField(blank=True, verbose_name="fonte de referência"),
        ),
    ]
