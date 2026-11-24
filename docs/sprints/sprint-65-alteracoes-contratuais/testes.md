# Testes — Sprint 65

## Critérios

- impactos vigentes recalculam valor e vigência atuais;
- anulação remove o impacto do cálculo sem apagar o registro;
- alteração que tornaria o valor negativo é recusada;
- dashboards e períodos respeitam a vigência atual.

## Execução local

Data: 24/11/2026.

- testes de valor e vigência atuais, anulação, efeito futuro e filtro por
  exercício — aprovados;
- suíte Django integral com PostgreSQL 17 temporário — **794 testes aprovados**
  em 108,099 segundos;
- configuração Django e migrations — aprovadas;
- scanner do repositório — aprovado;
- adaptador MCP — 6 testes aprovados;
- `git diff --check` — aprovado.

Nenhum banco real, sistema oficial, credencial, push ou deploy foi acessado.
