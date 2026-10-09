import os
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import connection


ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


class Command(BaseCommand):
    help = "Concede ao papel de runtime apenas os privilégios necessários."

    def handle(self, *args, **options):
        role = os.environ.get("DATABASE_RUNTIME_USER", "")
        if not ROLE_PATTERN.fullmatch(role):
            raise CommandError("DATABASE_RUNTIME_USER possui formato inválido")

        quoted_role = connection.ops.quote_name(role)
        statements = [
            f"GRANT USAGE ON SCHEMA public TO {quoted_role}",
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {quoted_role}",
            f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {quoted_role}",
            f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {quoted_role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {quoted_role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {quoted_role}",
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO {quoted_role}",
        ]
        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
        self.stdout.write(self.style.SUCCESS("Privilégios de runtime aplicados."))
