from django.db import migrations


def create_access_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="ADMINISTRADOR")
    Group.objects.get_or_create(name="FISCAL")


def retarget_admin_log_user_fk(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.conname, c.confrelid::regclass::text
              FROM pg_constraint c
              JOIN pg_attribute a
                ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
             WHERE c.conrelid = 'django_admin_log'::regclass
               AND c.contype = 'f'
               AND a.attname = 'user_id'
            """
        )
        row = cursor.fetchone()
        if not row or row[1] == "accounts_user":
            return
        constraint = schema_editor.quote_name(row[0])
        cursor.execute(f"ALTER TABLE django_admin_log DROP CONSTRAINT {constraint}")
        cursor.execute(
            f"""
            ALTER TABLE django_admin_log
            ADD CONSTRAINT {constraint}
            FOREIGN KEY (user_id) REFERENCES accounts_user(id)
            DEFERRABLE INITIALLY DEFERRED
            """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("admin", "0003_logentry_add_action_flag_choices"),
    ]

    operations = [
        migrations.RunPython(create_access_groups, migrations.RunPython.noop),
        migrations.RunPython(retarget_admin_log_user_fk, migrations.RunPython.noop),
    ]
