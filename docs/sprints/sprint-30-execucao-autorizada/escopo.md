# Sprint 30 — Execução autorizada pelo MCP com código de uso único

## Decisão do responsável

Aprovado por clique ("Autorizo tudo"): migração nova no `api_v1`, escopo
`fiscalsema.executar`, código de 10 minutos (5 tentativas), proposta do MCP
válida por 24 horas, pagamento nunca executado pela IA e, se os testes
passarem, PR + merge + `migrate-demo`.

## Fluxo

1. A IA usa `propor_rascunho` → rascunho PENDENTE, válido por 24 h, com o
   link de revisão. Nada é gravado.
2. A pessoa, logada, abre **Rascunhos IA**, confere antes/depois e clica em
   **Gerar código de confirmação** (aparece uma única vez, vale 10 minutos).
3. A pessoa digita o código no chat; a IA chama `executar_proposta`.
4. O sistema confere dono, mesmo cliente de IA, escopo `fiscalsema.executar`,
   validade da proposta e do código, até 5 tentativas; consome o código e
   grava pelos serviços oficiais, que revalidam permissão, regras de negócio
   e se o registro mudou depois da proposta.

Um "sim" no chat não executa nada.

## Proteções

- Código guardado só como HMAC (nunca em texto no banco, auditoria ou log).
- Uso único; nova chamada após executar devolve "já executada" (sem gravar de novo).
- `idempotency_key` opcional em `propor_rascunho` (única por pessoa).
- Pagamentos nunca recebem código nem são executados pela IA.
- A validade de 24 h vale também para o botão da tela.
- Rascunhos da API técnica (sem cliente MCP) seguem como antes.

## Fora do escopo

- Homologação, atesto, liquidação e autorização de pagamento: nunca por IA.
- Testes de compatibilidade por cliente e homologação (Sprint 31).
