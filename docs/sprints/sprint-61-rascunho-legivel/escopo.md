# Sprint 61 — Rascunho da IA escrito em português

## História de usuário

- **COMO:** fiscal de contrato que revisa propostas da IA externa (MCP);
- **QUERO:** ver o rascunho escrito em português, com o nome de cada campo,
  o valor de hoje e o valor proposto;
- **PARA:** conferir e decidir sem precisar ler código (JSON).

## Problema encontrado

A tela "Revisar rascunho" (`/rascunhos-ia/<id>/`) mostrava três blocos em
JSON — dados propostos, comparação e evidências — e, depois da aprovação, o
resultado da verificação também em JSON. O responsável pela demonstração
informou que os fiscais não sabem ler esse formato.

## Entregas

- tabela **"O que a IA está propondo"**: nome do campo como no formulário do
  sistema, valor de hoje, valor proposto e situação em palavras (Novo, Igual
  ao atual, Alterado, Diferente do atual — conferir, A IA deixou em branco,
  Precisa de confirmação, Pouco confiável — conferir), com destaque para
  campo importante e confirmação obrigatória;
- valores em reais (R$ 4.000,00), datas em dd/mm/aaaa e quantidades em
  formato brasileiro;
- lista **"De onde veio a informação"** com fonte, referência, campo, valor
  lido e trecho, em frases;
- depois da aprovação, **"Conferência feita pelo sistema"** em texto e tabela
  com a posição do contrato (empenhado, comprometido, executado, faturado,
  pago e saldo);
- o JSON original continua disponível, recolhido em **"Ver dados técnicos
  (para auditoria)"**.

## Fora do escopo

- regras de criação, validação, confirmação, rejeição, código de uso único,
  permissões e auditoria dos rascunhos: **sem alteração**;
- a IA continua sem executar pagamento, homologação ou qualquer gravação sem
  confirmação humana;
- lista de rascunhos (`/rascunhos-ia/`) e API/MCP: sem alteração.
