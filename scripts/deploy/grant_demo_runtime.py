"""Concede somente os privilégios necessários ao usuário de execução do demo."""

import os

import psycopg
from psycopg import sql


EXPECTED_DATABASE = "fiscalsema_demo"
EXPECTED_MIGRATOR = "fiscalsema_demo_migrator"
RUNTIME_ROLE = "fiscalsema_demo_app"


def main():
    database_url = os.environ.get("FISCALSEMA_DEMO_DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("FISCALSEMA_DEMO_DATABASE_URL não foi informada.")

    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database_name, database_user = cursor.fetchone()
            if database_name != EXPECTED_DATABASE or database_user != EXPECTED_MIGRATOR:
                raise SystemExit(
                    "Conexão recusada: a concessão exige o banco e o usuário "
                    "de migração exclusivos do demo."
                )

            runtime = sql.Identifier(RUNTIME_ROLE)
            database = sql.Identifier(EXPECTED_DATABASE)
            cursor.execute(sql.SQL("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
            cursor.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    database, runtime
                )
            )
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(runtime))
            cursor.execute(
                sql.SQL(
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
                    "IN SCHEMA public TO {}"
                ).format(runtime)
            )
            cursor.execute(
                sql.SQL(
                    "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}"
                ).format(runtime)
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
                ).format(runtime)
            )
            cursor.execute(
                sql.SQL(
                    "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                    "GRANT USAGE, SELECT ON SEQUENCES TO {}"
                ).format(runtime)
            )

    print("Privilégios mínimos do usuário de execução aplicados com sucesso.")


if __name__ == "__main__":
    main()
