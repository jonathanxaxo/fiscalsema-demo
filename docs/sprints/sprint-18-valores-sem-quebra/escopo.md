# Sprint 18 — Valores em R$ sem quebra

## Solicitação

Nos quadros "Como está meu contrato?", o "R$" de alguns valores ficava sozinho
na linha de cima do número. Corrigir para todos ficarem iguais e verificar se o
mesmo acontecia nas demais telas.

## Diagnóstico

Varredura com valores grandes (R$ 4.526.825.466,00) em 12 telas e três
larguras (1366 px, 1180 px e celular): o espaço comum entre "R$" e o número
permitia a quebra no painel, nas tabelas (contratos, OS, itens, empenhos, modo
tabela), nos quadros do relatório, na faixa de resumo do contrato e nos textos
do sino de notificações.

## Escopo

- trocar o espaço depois de "R$" por espaço que não quebra (`&nbsp;`) nas 121
  ocorrências de 17 templates e nos valores do sino (` `);
- quadros do painel, do relatório e da faixa de resumo: valor sempre em uma
  linha, com a letra ajustada à largura do quadro e algarismos de largura fixa;
- teste automático que impede a volta do espaço comum.

## Fora do escopo

Mensagens de validação dos serviços (texto de erro) e cálculos: não mudam.
Nenhuma migração.
