# Testes e evidências da Sprint 20

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos e de botões | `python manage.py test core.test_metodologia core.test_padrao_botoes --settings=core.settings_test --noinput` | 8 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **478 aprovados** (repetida após a segunda redução de tamanho) |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## Medição no navegador (Playwright: painel, contrato, lista de OS)

| | Antes | Depois |
|---|---|---|
| Alturas de botões e itens do menu (px) | 34, 40, 42 | 28, 32, 34 |
| Largura do menu lateral | 244 px | 208 px |
| Rolagem lateral (computador e iPhone 13) | não | não |

Página Metodologia conferida em 1366 px e iPhone 13, sem rolagem lateral.

## Capturas

`capturas/painel-desktop-antes.png` / `-depois.png`,
`capturas/os-desktop-antes.png` / `-depois.png`,
`capturas/metodologia-desktop-depois.png`.
