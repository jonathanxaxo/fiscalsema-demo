# Arquivos — Sprint 45

- `templates/accounts/base.html`: script do `<head>` marca o modo antes de desenhar a tela.
- `core/static/core/js/app.js`: modo padrão "Calmo" quando o sistema pede menos movimento; `still()` só no "Sem"; índice das barras do gráfico.
- `core/static/core/css/app.css`: bloqueio por `prefers-reduced-motion` limitado a `html:not([data-motion])`; camada "Sprint 45 — mais vida".
- `assistant/static/assistant/chat.css`: mesmo ajuste no chat.
- `core/test_movimento_sistema.py` (3 testes) — criado.
- `templates/core/metodologia.html`, `docs/sprints/README.md` e esta pasta.
