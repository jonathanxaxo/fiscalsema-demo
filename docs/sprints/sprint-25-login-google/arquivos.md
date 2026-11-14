# Arquivos da Sprint 25

| Arquivo | Mudança |
|---|---|
| `accounts/google_oidc.py` | novo: fluxo OpenID Connect (PKCE, state, nonce, troca e validação) |
| `accounts/google_views.py` | novo: entrar, retorno, confirmar vínculo, Minha conta, vincular, desvincular |
| `accounts/models.py`, `accounts/migrations/0009_google_identity.py` | `ExternalIdentity` e novos eventos de autenticação |
| `accounts/urls.py` | rotas `minha-conta/` e `google/*` |
| `accounts/test_google_login.py` | novo: 20 testes |
| `templates/accounts/login.html` | botão Google e mensagens |
| `templates/accounts/my_account.html`, `google_confirm_link.html` | novas telas |
| `templates/accounts/base.html` | link "Minha conta" no topo |
| `core/context_processors.py`, `core/settings_base.py`, `.env.example` | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` (secreto) |
| `core/static/core/css/app.css` | estilos do botão Google e de Minha conta |
| `templates/core/metodologia.html` | Sprint 25 e controle de segurança |
| `docs/sprints/README.md`, esta pasta | registro |
