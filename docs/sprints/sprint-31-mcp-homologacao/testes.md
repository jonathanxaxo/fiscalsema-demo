# Testes — Sprint 31 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test api_v1.test_mcp_seguranca` | 20 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 615 testes OK |
