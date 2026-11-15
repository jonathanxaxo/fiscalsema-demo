# Testes — Sprint 51

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **708 testes OK** |

Novos (em `accounts/test_sessao_inatividade.py`): configuração ligada por
padrão; cookie de login sem `expires`/`max-age`; Arise responde a regra
básica (fechar o navegador encerra, fechar só uma aba não).

## Navegador (Playwright)

- cookie de login do tipo "sessão" (expira ao fechar o navegador);
- navegador fechado e aberto de novo → `/contratos/` levou para
  `/conta/entrar/?next=/contratos/` (pediu a senha).
