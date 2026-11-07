# Testes e evidências da Sprint 14

| Verificação | Comando | Resultado |
|---|---|---|
| Testes do sino | `core.test_notificacoes` | 7 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **455 aprovados** (448 + 7) |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

## Navegador (Playwright, contrato fictício 000885/2026)

| Verificação | Computador | Celular (iPhone 13) |
|---|---|---|
| Contagem no sino | 14 | 14 |
| Botão "Sair" visível com o painel aberto | sim | sim |
| Fecha com Esc | sim | sim |
| Títulos cortados (1ª captura) | **sim — defeito** | **sim — defeito** |
| Títulos cortados (após correção) | 0 | 0 |

Capturas em `capturas/`.
