# Testes e evidências da Sprint 06

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test core.test_identidade_visual --settings=core.settings_test` | 3 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **416 aprovados** (413 + 3 novos) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Arquivos estáticos (modo Vercel) | `python manage.py collectstatic --noinput --settings=core.settings_demo` | 133 copiados; `logo.svg` e `favicon.svg` versionados |
| Favicon no navegador | Playwright | HTTP 200, `image/svg+xml` |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |
| Capturas | Playwright, computador e iPhone 13 | 4 em `capturas/` |

## Problema encontrado (anterior a esta sprint)

No celular, o menu aberto começa a 64 px do topo da janela, mas a faixa de
demonstração ocupa duas linhas; por isso o menu cobre o cabeçalho
(`capturas/03-menu-celular-depois.png`). O menu continua utilizável (fecha ao
tocar fora ou com Esc). Registrado para a próxima sprint.
