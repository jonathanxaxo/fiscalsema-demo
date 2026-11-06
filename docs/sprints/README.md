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
