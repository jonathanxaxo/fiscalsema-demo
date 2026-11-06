# Organização por sprints

Cada sprint deve possuir uma pasta `sprint-NN-nome` com:

- `escopo.md`: objetivo e limites;
- `arquivos.md`: arquivos criados, alterados e removidos;
- `decisoes.md`: decisões e riscos aceitos;
- `testes.md`: comandos e resultados verificáveis.

Correções futuras criam nova sprint; não reescrevem silenciosamente o histórico
documental das entregas anteriores.

## Sprints registradas

- `sprint-01-vercel-minima`: cópia independente, sanitização, adaptação para
  Vercel e validações sem banco;
- `sprint-02-integracao-postgresql`: primeiro commit local e preparação dos
  testes integrais em PostgreSQL exclusivo.
- `sprint-03-governanca-agente`: criação do `CLAUDE.md` com as regras de
  trabalho, segurança e registro para agentes de IA.
- `sprint-04-diagnostico-visual`: execução local com dados fictícios,
  capturas de tela e lista priorizada de melhorias visuais.
- `sprint-05-correcoes-leitura`: tabelas sem quebra de palavras, aviso de
  rolagem, formatação de exercício, quantidades e CNPJ/CPF.
- `sprint-06-identidade-visual`: logotipo, favicon e ícones SVG próprios,
  faixa de demonstração em âmbar e nome FiscalSema nos títulos.
- `sprint-07-padronizacao-telas`: listas operacionais padronizadas, ações do
  contrato no topo, formulários em duas colunas, rascunhos da IA no layout do
  sistema e correção do menu móvel.
- `sprint-08-painel`: prioridades no topo do painel e barra de atalhos.
- `sprint-09-publicacao`: registro do PR nº 3, CI, Preview, merge e
  conferência da produção.
