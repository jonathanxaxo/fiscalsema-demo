# Arquivos — Sprint 30

## Criados
- `api_v1/execucao.py` — emissão do código, conferência e execução.
- `api_v1/migrations/0005_execucao_autorizada.py` — validade, chave de repetição, hash do código, tentativas e eventos novos.
- `docs/sprints/sprint-30-execucao-autorizada/*`.

## Alterados
- `api_v1/models.py`, `api_v1/drafts.py` (validade e canal na confirmação).
- `api_v1/mcp_remoto.py` — `executar_proposta`, `idempotency_key`, link de revisão.
- `api_v1/web_views.py`, `api_v1/web_urls.py`, `templates/api_v1/draft_detail.html`.
- `core/settings_base.py` — escopo `fiscalsema.executar` e prazos.
- `core/static/core/css/app.css`, `api_v1/test_mcp_remoto.py` (9 testes novos).
- `templates/core/metodologia.html`, `docs/sprints/README.md`, `docs/seguranca/controles.md`.
