from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contracts", "0017_contractitem_calculation_provenance"),
    ]

    operations = [
        migrations.AddField(
            model_name="contractitem",
            name="annual_reference_quantity",
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                help_text="Referência documental; não altera o valor total do item.",
                max_digits=24,
                null=True,
                verbose_name="quantidade de referência por ano contratual",
            ),
        ),
        migrations.AddField(
            model_name="contractitem",
            name="annual_operational_limit",
            field=models.DecimalField(
                blank=True,
                decimal_places=4,
                help_text="Quantidade máxima de OS em cada ano da vigência.",
                max_digits=20,
                null=True,
                verbose_name="limite operacional por ano contratual",
            ),
        ),
        migrations.AddField(
            model_name="contractitem",
            name="annual_reference_unit",
            field=models.CharField(
                blank=True,
                max_length=120,
                verbose_name="unidade da referência anual",
            ),
        ),
        migrations.AddConstraint(
            model_name="contractitem",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(annual_reference_quantity__isnull=True)
                    | models.Q(annual_reference_quantity__gt=Decimal("0"))
                ),
                name="contracts_item_annual_reference_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="contractitem",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(annual_operational_limit__isnull=True)
                    | models.Q(annual_operational_limit__gt=Decimal("0"))
                ),
                name="contracts_item_annual_limit_positive",
            ),
        ),
    ]
