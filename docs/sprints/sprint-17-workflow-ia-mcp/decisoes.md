# Decisões da Sprint 17

## Decisões

1. O MCP é um adaptador externo e não importa Django.
2. Todo acesso passa pela API e por credencial revogável.
3. O token existe somente em `FISCALSEMA_API_TOKEN`.
4. `.mcp.json` contém apenas URL demonstrativa, nunca segredo.
5. A única ferramenta de escrita cria `AssistantDraft`.
6. Confirmação e rejeição continuam exclusivas da interface autenticada.
7. Os serviços oficiais revalidam autorização, regras e concorrência.
8. A interface existente é evoluída; nenhum fluxo paralelo é criado.
9. Nenhuma nova dependência é necessária.

## Riscos e controles

| Risco | Controle |
|---|---|
| Token exposto | variável de ambiente e ausência em respostas |
| Agente exceder autonomia | lista fechada de ferramentas |
| Ação automática | MCP não possui ferramenta de confirmação |
| Acesso fora do escopo | autorização reavaliada pela API |
| Dado desatualizado | verificação de concorrência na confirmação |
| Contexto excessivo | ferramentas específicas e respostas paginadas |
| Dado real na demonstração | scanner e regra de dados fictícios |
| Alteração financeira indevida | serviços determinísticos do backend |
