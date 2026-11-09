# Testes e evidências da Sprint 18

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test core.test_valores_sem_quebra --settings=core.settings_test --noinput` | 4 aprovados |
| Suíte integral (1ª execução) | `python manage.py test --settings=core.settings_test --noinput` | 464, 2 falhas esperadas (asserções antigas com espaço comum) |
| Suíte integral final | mesmo comando | **464 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## Varredura no navegador (Playwright, valores fictícios grandes injetados)

Para cada valor em R$ das 12 telas, verificou-se se o "R$" e o número ficavam
em linhas diferentes, em 1366 px, 1180 px e iPhone 13.

| Situação | Antes | Depois |
|---|---|---|
| Computador (1366 px) | quebra em 7 telas (painel 26 valores) | nenhuma |
| Notebook (1180 px) | quebra em 7 telas | nenhuma |
| Celular | quebra em 12 telas | nenhuma |
| Valores transbordando o quadro | — | 0 (painel e relatório, computador e celular) |

A varredura foi conferida contra a versão anterior para garantir que detecta
o problema.

## Capturas

`capturas/painel-desktop-antes.png` / `-depois.png`,
`capturas/painel-celular-antes.png` / `-depois.png`,
`capturas/relatorio-desktop-antes.png` / `-depois.png`.
