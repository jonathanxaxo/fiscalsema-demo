# Arquivos — Sprint 74

## Criados

- `assistant/test_sugestoes_contrato.py` — testes da Sprint 74;
- `docs/sprints/sprint-74-arise-relatorios/` — escopo, decisões, arquivos,
  testes e capturas.

## Alterados

- `assistant/conhecimento.py` — `CONTRACT_SUGGESTIONS`,
  `suggestions_for(..., contract=)` e `contract_suggestions_for`;
- `assistant/context_processors.py`, `assistant/views.py` e
  `templates/assistant/flutuante.html` — sugestões conforme o contrato ativo;
- `assistant/static/assistant/chat.css` — destaque do contrato ativo;
- `core/static/core/css/app.css` — impressão dos relatórios;
- `templates/contracts/administrative_portfolio_report.html` — texto do aviso;
- `templates/core/metodologia.html`, `docs/sprints/README.md` e
  `docs/sprints/sprint-73-painel-central/testes.md` — registro.
