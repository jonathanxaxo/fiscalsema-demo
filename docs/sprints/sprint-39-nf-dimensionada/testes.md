# Testes — Sprint 39 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test contracts.test_nf_dimensionada` | 6 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 664 testes OK |
