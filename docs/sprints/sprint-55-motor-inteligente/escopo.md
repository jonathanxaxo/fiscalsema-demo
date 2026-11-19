# Sprint 55 — Motor inteligente contratual

## Objetivo

Criar um motor determinístico, auditável e supervisionado para classificar
contratos, verificar dados estruturados e notificar divergências, sem inventar
regras jurídicas e sem executar correções automaticamente.

## Entregas

- classificação separada por modalidade de execução e categoria gerencial;
- categorias gerenciais como Sistema, Equipamento, Serviço continuado,
  Serviço sob demanda e Entrega única;
- modalidade por item, inclusive contratos mistos;
- cláusulas e regras candidatas com documento-fonte, referência, versão e
  confirmação humana;
- calculadora tipada somente para regra confirmada;
- conferência do contrato PDF contra número, processo e fornecedor
  cadastrados, emitindo notificação em vez de alterar o registro;
- achados com gravidade, estado, justificativa e resolução/reabertura
  auditadas;
- reaproveitamento dos cálculos financeiros e alertas já existentes.

## Limites

- nenhuma interpretação legal automática;
- nenhuma regra sem fonte e confirmação humana;
- nenhuma correção automática do contrato;
- nenhuma homologação, atesto ou pagamento pela IA.
