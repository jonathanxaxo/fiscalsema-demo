# Matriz de autonomia

| Cenário | Agente/MCP | Aprovação humana | Execução |
|---|---|---|---|
| Consultar contrato autorizado | Pode consultar | Não exigida | Somente leitura |
| Resumir pendências fictícias | Pode analisar | Não exigida | Somente leitura |
| Propor criação ou atualização | Pode criar rascunho | Obrigatória | Não executada pelo MCP |
| Confirmar ou rejeitar proposta | Não pode | Obrigatória na interface | Backend autorizado |
| Homologar, atestar ou pagar | Não pode | Fora do escopo da integração | Não disponível |

Quanto maior o impacto, menor a autonomia do agente e maior a exigência de
validação, autorização, auditoria e evidência.
