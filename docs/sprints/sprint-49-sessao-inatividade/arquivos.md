# Arquivos — Sprint 49

- `accounts/middleware.py`: `IdleSessionTimeoutMiddleware`.
- `accounts/views.py` e `accounts/urls.py`: `sessao/ativa/` (sinal de uso; só responde 204, não altera dados).
- `core/settings_base.py`: middleware na lista e `SESSION_IDLE_TIMEOUT_SECONDS`.
- `core/context_processors.py`: tempo enviado às telas.
- `templates/accounts/base.html`: `data-idle-timeout` e `data-keepalive-url` no `<body>` (só logado).
- `core/static/core/js/app.js`: relógio de inatividade e sinal de uso.
- `accounts/test_sessao_inatividade.py` (7 testes) — criado.
- `docs/seguranca/controles.md`, `templates/core/metodologia.html`, `docs/sprints/README.md` e esta pasta.
