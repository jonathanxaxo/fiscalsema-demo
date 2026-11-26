# Arquivos — Sprint 71

| Arquivo | Alteração |
|---|---|
| `assistant/contexto_contrato.py` | Resolve e valida o contrato ativo no escopo autorizado |
| `assistant/context_processors.py` | Disponibiliza o contexto validado ao chat flutuante |
| `assistant/models.py` e `assistant/migrations/0002_...py` | Vinculam opcionalmente cada conversa ao contrato, sem copiar valores |
| `assistant/views.py` | Rejeita contexto indevido e isola a conversa na troca de contrato |
| `assistant/prompt.py` | Declara o contrato ativo como contexto de referência do backend |
| `assistant/static/assistant/chat.js` | Reseta no navegador o histórico incompatível com o contrato atual |
| `assistant/static/assistant/chat.css` | Apresenta o contexto de forma compacta |
| `templates/assistant/*.html` | Exibe e propaga o contrato ativo no chat flutuante e na tela cheia |
| `templates/accounts/base.html` | Entrega ao widget o contrato selecionado pela tela atual |
| `assistant/test_contexto_contrato.py` | Regressão automatizada de seleção, autorização e isolamento |
| `assistant/conhecimento/16-chat-arise.md` | Explica ao usuário a troca de contexto |
| `docs/seguranca/controles.md` | Registra o controle de isolamento contratual |
| `docs/sprints/README.md` e `templates/core/metodologia.html` | Registram a Sprint 71 |

Não há dependência nova. A migração adiciona apenas uma chave estrangeira
opcional na conversa; documentos e valores contratuais não são duplicados.
