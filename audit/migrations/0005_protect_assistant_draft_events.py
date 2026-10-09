from django.db import migrations


def protect(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute("""CREATE TRIGGER fiscalsema_audit_immutable
        BEFORE UPDATE OR DELETE ON api_v1_assistantdraftevent
        FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();""")


def unprotect(apps, schema_editor):
    schema_editor.execute("DROP TRIGGER IF EXISTS fiscalsema_audit_immutable ON api_v1_assistantdraftevent;")


class Migration(migrations.Migration):
    dependencies = [("audit", "0004_protect_api_access_events"), ("api_v1", "0002_assistantdraft_assistantdraftevent")]
    operations = [migrations.RunPython(protect, unprotect)]
