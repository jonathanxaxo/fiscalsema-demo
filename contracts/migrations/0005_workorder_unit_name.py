from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0004_workorder_workorderevent_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="workorder",
            name="unit_name",
            field=models.CharField(
                default="",
                editable=False,
                max_length=50,
                verbose_name="unidade de referência",
            ),
            preserve_default=False,
        ),
    ]
