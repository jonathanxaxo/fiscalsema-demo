# Arquivos da Sprint 21

| Arquivo | Mudança |
|---|---|
| `assistant/` (novo app) | `models.py`, `migrations/0001_conversas.py`, `provedor.py`, `conhecimento.py`, `conhecimento/*.md` (11 seções), `prompt.py`, `limites.py`, `ferramentas.py` (desligado), `views.py`, `urls.py`, `context_processors.py`, `static/assistant/chat.js` e `chat.css`, `tests.py`, `test_provedor.py` |
| `templates/assistant/chat.html` | tela do chat |
| `core/settings_base.py` | app, context processor e configurações `ASSISTANT_*` |
| `core/urls.py` | rota `assistente/` |
| `templates/accounts/base.html` | item "Assistente IA" no menu (só quando configurado) |
| `templates/core/icone_menu.html` | ícone "assistente" |
| `audit/services.py` | rótulo "Assistente IA — pergunta" na auditoria |
| `vercel.json` | `"regions": ["gru1"]` (São Paulo), igual ao projeto de referência — autorizado pelo responsável |
| `.env.example` | nomes das variáveis (sem valores secretos) |
| `templates/core/metodologia.html` | Sprint 21, Gemini, Assistente IA, testes e privacidade |
| `core/test_metodologia.py` | teste: sprint mais recente precisa estar na Metodologia |
| `CLAUDE.md`, `AGENTS.md` | regra "Metodologia sempre atualizada" |
| `docs/seguranca/controles.md`, `docs/sprints/README.md`, esta pasta | documentação |

Dependências novas: **nenhuma**.
