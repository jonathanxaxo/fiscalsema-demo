# Testes — Sprint 28 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test api_v1.test_mcp_remoto` | 21 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 580 testes OK |

Cobertura dos testes novos: metadados, 401 com `resource_metadata`, rotas de
gestão não publicadas, registro dinâmico seguro e limitado, login obrigatório,
PKCE obrigatório, cancelar sem código, token guardado como hash, rotação e
reuso da renovação, ferramentas por escopo, isolamento entre pessoas,
rascunho só pendente, JSON inválido, limite por minuto, conta bloqueada,
token expirado e revogação pela Minha conta.
