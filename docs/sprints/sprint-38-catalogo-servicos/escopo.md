# Sprint 38 — Catálogo de serviços, memória de cálculo e ciclo do serviço na OS

Referência: FiscalSema Light (ADR 0021 e parte da 0022), somente lido e reescrito no Demo.

## Autorização

Escolhido por clique ("Catálogo, ciclo e NF"), com execução em sequência
autorizada. Dividido em duas sprints para mudanças menores: esta (catálogo e
ciclo do serviço) e a 39 (NF ligada aos serviços, valor dimensionado e devolução).

## Incluído

- Novas unidades de item: **UST, HST e USN**.
- **Catálogo de serviços do contrato**: código, serviço, unidade de medida,
  peso por complexidade (baixa, média, alta; vazio = N/A), fonte e situação;
  alterações registradas na auditoria do contrato. Acesso pelo botão
  "Catálogo de serviços" na ficha do contrato.
- **Memória de cálculo da OS** (OS medidas em quantidade): serviço ×
  complexidade × quantidade; o peso é copiado e congelado na OS; a quantidade
  da OS passa a ser a soma das unidades (UST/HST/USN) e fica bloqueada na
  edição; as mesmas validações de saldo da edição da OS valem para cada
  inclusão, alteração e remoção.
- **Ciclo de cada serviço**: Em andamento → Entregue → Aceito → Homologado
  (com número do Termo de Homologação); recusa volta para ajuste com motivo
  obrigatório; datas não futuras, não anteriores à abertura nem ao passo
  anterior; "Homologar todos os aceitos" com um único termo.
- Relatório com a memória de cálculo das OS.

Homologação aqui é o registro do Termo assinado por pessoa; a IA continua sem
poder homologar (Sprints 28–31).

## Migração

`contracts/0022_catalogo_servicos_os`: cria 2 tabelas e acrescenta opções de
unidade e de evento; nenhum registro existente é alterado.
