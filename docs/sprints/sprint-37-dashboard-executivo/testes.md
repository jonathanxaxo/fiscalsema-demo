# Testes — Sprint 37 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test contracts.test_dashboard_executivo` | 4 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 649 testes OK (após corrigir "R$" sem quebra nas dicas do gráfico) |

Captura no navegador (1366 px) com contrato fictício: todas as seções
exibidas, contagem de dias e gráfico mensal.
