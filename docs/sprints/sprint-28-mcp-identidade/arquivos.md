# Arquivos — Sprint 28

## Criados
- `api_v1/oauth.py` — permissão do registro dinâmico, auditoria, conexões e revogação.
- `api_v1/oauth_urls.py` — rotas OAuth publicadas (somente as necessárias).
- `api_v1/mcp_remoto.py` — endpoint `/mcp` e ferramentas.
- `api_v1/migrations/0004_mcp_oauth.py` — rascunho ligado ao cliente OAuth e novos tipos de evento.
- `api_v1/test_mcp_remoto.py` — 21 testes.
- `templates/oauth2_provider/authorize.html` — consentimento.
- `docs/sprints/sprint-28-mcp-identidade/*`.

## Alterados
- `requirements.txt` — django-oauth-toolkit 3.4.1 e dependências fixadas.
- `core/settings_base.py` — `oauth2_provider`, `OAUTH2_PROVIDER`, limites MCP.
- `core/urls.py` — rotas OAuth e `/mcp`.
- `api_v1/models.py`, `api_v1/drafts.py`, `api_v1/apps.py`.
- `accounts/google_views.py`, `accounts/urls.py`, `templates/accounts/my_account.html`.
- `core/static/core/css/app.css`, `templates/core/metodologia.html`.
- `docs/sprints/README.md`, `docs/seguranca/controles.md`.
