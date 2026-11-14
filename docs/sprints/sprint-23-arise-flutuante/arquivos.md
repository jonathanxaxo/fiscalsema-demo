# Arquivos da Sprint 23

| Arquivo | Mudança |
|---|---|
| `templates/assistant/flutuante.html` | novo: ícone e painel flutuante |
| `templates/accounts/base.html` | carrega o CSS/JS do assistente e inclui o painel (com login e assistente ativo) |
| `templates/assistant/chat.html` | nome e remoção do carregamento duplicado de CSS/JS |
| `assistant/static/assistant/chat.js` | várias instâncias (página e painel), abrir/fechar, Esc, continuar conversa, nova conversa |
| `assistant/static/assistant/chat.css` | estilos do ícone e do painel (desktop e celular, oculto na impressão) |
| `assistant/context_processors.py` | `assistant_widget` e sugestões por perfil |
| `assistant/views.py`, `assistant/urls.py` | `GET conversas/<id>/mensagens/` (só do dono) |
| `assistant/prompt.py`, `assistant/conhecimento/*.md`, `audit/services.py`, demais arquivos do app | nome "Assistente Arise" |
| `assistant/tests.py`, `core/test_metodologia.py` | testes do painel, do endpoint e da nova seção |
| `templates/core/metodologia.html`, `core/static/core/css/app.css` | seção "Como o Assistente Arise foi construído" e Sprint 23 |
| `docs/sprints/README.md`, esta pasta | registro |
