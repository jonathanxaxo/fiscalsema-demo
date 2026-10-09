from django.db import migrations


def protect_events(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute(
        """CREATE TRIGGER fiscalsema_audit_immutable
        BEFORE UPDATE OR DELETE ON contracts_fiscalsubstitutionevent
        FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();"""
    )


def unprotect_events(apps, schema_editor):
    schema_editor.execute(
        "DROP TRIGGER IF EXISTS fiscalsema_audit_immutable "
        "ON contracts_fiscalsubstitutionevent;"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0005_protect_assistant_draft_events"),
        ("contracts", "0014_fiscalsubstitution_fiscalsubstitutionevent"),
    ]

    operations = [migrations.RunPython(protect_events, unprotect_events)]
