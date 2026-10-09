import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_fiscal_registration"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="organizations.organization",
                verbose_name="organização",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="sector",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="organizations.sector",
                verbose_name="setor",
            ),
        ),
    ]
