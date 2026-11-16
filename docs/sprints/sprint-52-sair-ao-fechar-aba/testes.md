# Testes — Sprint 52

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **711 testes OK** |

Novos: atributos só para quem está logado; encerramento com auditoria e
mensagem; só POST com CSRF (GET → 405; sem CSRF → 403 e sessão mantida).

## Navegador (Playwright, navegador sempre aberto)

| Passo | Resultado |
|---|---|
| Entrou com a senha | Painel |
| Atualizou (F5) | continuou logado |
| Trocou de tela | continuou logado |
| Ctrl+clique (nova aba) | continuou logado |
| Fechou a aba do sistema e abriu de novo | pediu a senha, com a mensagem |
| Digitou a senha | voltou para a tela pedida |
| Atualizou de novo | continuou logado |
