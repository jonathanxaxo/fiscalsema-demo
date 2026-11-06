# Testes e evidências da Sprint 04

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte integral (linha de base) | `python manage.py test --settings=core.settings_test --noinput --parallel 4` | **408 testes aprovados** (PostgreSQL 16 local descartável) |
| Migrations no banco local | `python manage.py migrate --settings=core.settings_development` | aplicadas sem erro |
| Capturas de tela | Playwright (Chromium) — computador 1366×800 e iPhone 13 | 16 capturas; 8 versionadas em `capturas-antes/` |
| Páginas visitadas | login, painel, contratos, detalhe, itens, OS, empenhos, cadastro | todas HTTP 200 |
| Auditoria do repositório | `python scripts/security/scan_repository.py` | `PASS` |

Ambiente: máquina temporária da nuvem, Python 3.13, Django 5.2.17, PostgreSQL
16. Nenhum banco, dado ou serviço real foi acessado.
