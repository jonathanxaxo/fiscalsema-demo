# Sprint 40 — Arise e IA externa conhecem as funções das Sprints 35 a 39

## Pedido do responsável

"Quero saber se, com todas essas melhorias, o chat e as demais funções irão
funcionar e se o chat terá base de conhecimento das novas funções." A análise
mostrou que tudo funcionava (664 testes), mas o Arise não tinha ajuda sobre as
funções novas e a IA externa (MCP) não recebia os campos novos. Autorizado por
clique ("Autorizo tudo").

## Incluído

- Base de conhecimento do Arise: seções novas
  `12-dashboard-executivo`, `13-prazos-os`, `14-catalogo-servicos` e
  `15-nf-dimensionada`; Dashboard no menu (`00`), avisos novos (`01`) e
  máscara de CPF/CNPJ (`02`).
- IA externa (MCP/API): a OS passa a trazer prazo da fábrica, horas gastas
  informadas, situação do prazo com contagem de dias e a memória de cálculo
  (serviços); a NF traz se foi devolvida (e não entra nos cálculos), motivo,
  NF substituída, serviços cobrados e valor dimensionado.
- Instruções do servidor MCP explicam NF devolvida e valor dimensionado.

Sem migração e sem dependência nova. A IA continua sem homologar, devolver,
confirmar ou pagar.
