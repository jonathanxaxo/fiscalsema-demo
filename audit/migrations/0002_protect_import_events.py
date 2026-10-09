from django.db import migrations


def protect_import_events(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute(
        """
        CREATE TRIGGER fiscalsema_audit_immutable
        BEFORE UPDATE OR DELETE ON data_imports_importevent
        FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();
        """
    )


def unprotect_import_events(apps, schema_editor):
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS fiscalsema_audit_immutable ON data_imports_importevent;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_protect_audit_events"),
        ("data_imports", "0001_initial"),
    ]
    operations = [migrations.RunPython(protect_import_events, unprotect_import_events)]
