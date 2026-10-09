from django.db import migrations


def protect_api_access_events(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute(
        """CREATE TRIGGER fiscalsema_audit_immutable
        BEFORE UPDATE OR DELETE ON api_v1_apiaccessevent
        FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();"""
    )


def unprotect_api_access_events(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER IF EXISTS fiscalsema_audit_immutable ON api_v1_apiaccessevent;")


class Migration(migrations.Migration):
    dependencies = [("audit", "0003_protect_csv_export_events"), ("api_v1", "0001_initial")]
    operations = [migrations.RunPython(protect_api_access_events, unprotect_api_access_events)]
