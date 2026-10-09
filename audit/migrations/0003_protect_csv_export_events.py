from django.db import migrations


def protect_csv_export_events(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute(
        """
        CREATE TRIGGER fiscalsema_audit_immutable
        BEFORE UPDATE OR DELETE ON contracts_csvexportevent
        FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();
        """
    )


def unprotect_csv_export_events(apps, schema_editor):
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS fiscalsema_audit_immutable ON contracts_csvexportevent;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0002_protect_import_events"),
        ("contracts", "0013_csvexportevent"),
    ]
    operations = [migrations.RunPython(protect_csv_export_events, unprotect_csv_export_events)]
