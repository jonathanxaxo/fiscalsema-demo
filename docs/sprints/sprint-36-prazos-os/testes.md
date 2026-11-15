# Testes — Sprint 36 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test contracts.test_prazos_os` | 8 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 645 testes OK |
