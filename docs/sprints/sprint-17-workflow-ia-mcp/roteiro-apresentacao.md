# Roteiro de apresentação — Piloto IA 07

## 1. Contexto

O FiscalSema Demo usa somente dados fictícios e demonstra fiscalização
contratual sem conexão com ambiente institucional real.

## 2. Problema demonstrado

Um agente precisa consultar uma demanda, propor uma ação e manter controle
humano antes de qualquer alteração.

## 3. Componentes

- Django e PostgreSQL demonstrativo;
- API autenticada e limitada por contrato;
- adaptador MCP;
- rascunho da IA;
- tela de revisão humana;
- serviços oficiais e auditoria.

## 4. Demonstração

1. Consultar contratos autorizados pelo MCP.
2. Consultar resumo e pendências de um contrato fictício.
3. Enviar uma proposta com `propor_rascunho`.
4. Mostrar a resposta `executada: false`.
5. Abrir “Rascunhos da IA”.
6. Conferir origem, confiança, comparação e evidências.
7. Rejeitar uma proposta de teste ou confirmar outra.
8. Mostrar o resultado e o evento de auditoria.

## 5. Mensagem principal

A IA prepara e explica. A pessoa autorizada decide. O backend revalida e
executa. Todo o fluxo permanece rastreável.

## 6. Limitações honestas

- ambiente exclusivamente demonstrativo;
- dados fictícios;
- MCP não confirma ações;
- nenhum acesso direto ao banco;
- nenhum pagamento ou homologação é delegado à IA.
