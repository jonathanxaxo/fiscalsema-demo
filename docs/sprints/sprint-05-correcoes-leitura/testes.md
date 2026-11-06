# Testes e evidências da Sprint 05

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos dos filtros | `python manage.py test core.test_formatacao --settings=core.settings_test` | 5 aprovados |
| Primeira execução da suíte | `python manage.py test --settings=core.settings_test --noinput` | 413 executados, **1 falha esperada** (`"100,0000"` no formato antigo) |
| Suíte após atualizar o teste | mesmo comando | **413 aprovados** (408 anteriores + 5 novos) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |
| Verificação no navegador (Playwright) | páginas renderizadas com dados fictícios | exercício `2026` (sem `2.026`); CNPJ `12.345.678/0001-99`; "Etapa 19" ausente; itens `1.200,00` sem `,0000` |
| Capturas depois | Playwright, computador e iPhone 13 | 5 versionadas em `capturas-depois/` |

Comparar com `docs/sprints/sprint-04-diagnostico-visual/capturas-antes/`.

Ambiente: máquina temporária da nuvem, PostgreSQL 16 local descartável.
