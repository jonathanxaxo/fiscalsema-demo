from django.db import migrations


AUDIT_TABLES = (
    "accounts_authenticationevent",
    "organizations_organizationevent",
    "contracts_contractevent",
    "contracts_contractitemevent",
    "contracts_budgetcommitmentevent",
    "contracts_workorderevent",
    "contracts_workorderallocationevent",
    "contracts_workorderexecutionevent",
    "contracts_invoiceevent",
    "contracts_paymentevent",
    "contracts_contractsharingevent",
    "documents_documentevent",
)


def protect_audit_events(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        raise RuntimeError("A proteção imutável de auditoria exige PostgreSQL.")
    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION fiscalsema_prevent_audit_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Registros de auditoria são imutáveis.' USING ERRCODE = '55000';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in AUDIT_TABLES:
        schema_editor.execute(
            f"""
            CREATE TRIGGER fiscalsema_audit_immutable
            BEFORE UPDATE OR DELETE ON {schema_editor.quote_name(table)}
            FOR EACH ROW EXECUTE FUNCTION fiscalsema_prevent_audit_mutation();
            """
        )


def unprotect_audit_events(apps, schema_editor):
    for table in AUDIT_TABLES:
        schema_editor.execute(
            f"DROP TRIGGER IF EXISTS fiscalsema_audit_immutable ON {schema_editor.quote_name(table)};"
        )
    schema_editor.execute("DROP FUNCTION IF EXISTS fiscalsema_prevent_audit_mutation();")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_user_organization_sector"),
        ("organizations", "0001_initial"),
        ("contracts", "0011_alter_contractsharingevent_event_type"),
        ("documents", "0002_documentevent"),
    ]

    operations = [migrations.RunPython(protect_audit_events, unprotect_audit_events)]
