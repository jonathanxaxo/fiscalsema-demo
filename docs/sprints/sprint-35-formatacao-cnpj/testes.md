# Testes — Sprint 35 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test contracts.test_formatacao_sprint35` | 5 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 637 testes OK |
