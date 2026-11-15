# Testes — Sprint 47

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **688 testes OK** |

## Navegador (Playwright, dados fictícios)

- clique na coluna "Item" de uma linha da lista → abriu a OS;
- clique no número da OS → abriu a OS;
- "Cadastrar Nota Fiscal" no topo → abriu o formulário da NF da OS;
- "Editar OS" no topo → abriu a edição da OS.
