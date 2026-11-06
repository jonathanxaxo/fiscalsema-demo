# Escopo da Sprint 12 — Dados fictícios de apresentação

## História de usuário

- **COMO:** responsável pela demonstração
- **QUERO:** o contrato 000885/2026 preenchido com dados fictícios
- **PARA:** apresentar o painel do Fiscal com saldos, alertas e prazos reais

## Decisões do responsável (por clique)

- pacote completo: 3 itens, 2 empenhos, 5 OS, execuções, 2 NFs e 1 pagamento;
- exceção autorizada à regra de não criar dados fictícios, ciente de que os
  dados não podem ser apagados.

## Entregas

- comando `seed_demo_presentation`;
- fluxo manual `.github/workflows/seed-demo-presentation.yml`;
- testes e instruções em `docs/operacao/demo.md`.

## Limites

- usa somente os serviços de negócio (mesmas validações e auditoria da tela);
- não altera dados já existentes do contrato; apenas acrescenta;
- sem migration; sem bibliotecas.

## Estado

Implementada e testada; aguardando PR, merge e execução do fluxo.
