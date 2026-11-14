# Testes e evidências da Sprint 25

| Verificação | Comando | Resultado |
|---|---|---|
| Login Google | `python manage.py test accounts.test_google_login --settings=core.settings_test --noinput` | 20 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **538 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração / auditoria | `check`, `scan_repository.py` | sem problemas / `PASS` |
| Migrations | `makemigrations --check --dry-run` | sem pendências (`accounts/0009` criada nesta sprint) |

Cenários cobertos (Google simulado, sem internet): PKCE/state/nonce; botão
oculto sem configuração; usuário já vinculado entra sem alterações; bloqueado
e pendente recusados; mesmo e-mail exige senha (errada → não vincula; certa →
vincula e entra); vínculo pendente expira; e-mail sem cadastro recusado sem
criar usuário; tokens inválidos (e-mail não verificado, outro aplicativo,
emissor, expirado, nonce); state adulterado não chama o Google; falha do
provedor; cancelamento; vincular por Minha conta exige senha; Google de outro
usuário recusado; desvincular exige senha; não remove o único método de
acesso; não desvincula identidade de outro usuário; perfil nunca alterado.

Navegador: login com o botão Google e Minha conta conferidos no computador e
no celular, sem rolagem lateral (`capturas/`).
