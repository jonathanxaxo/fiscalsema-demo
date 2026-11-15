# Testes — Sprint 48

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **692 testes OK** |

Novos: `contracts/test_linhas_clicaveis.py` (4 testes).

## Navegador (Playwright)

- varredura de 40 telas listando as linhas clicáveis e o destino (tabela do escopo);
- botão "Dashboard" dentro da linha do contrato → continua indo ao painel;
- clique no fornecedor → abre o cadastro do contrato;
- botão "Abrir" da lista de OS → continua abrindo a OS;
- rateio dentro do empenho → abre a OS; linha da NF dentro da OS → abre a NF;
- Ctrl + clique → abre em nova aba e mantém a tela atual.
