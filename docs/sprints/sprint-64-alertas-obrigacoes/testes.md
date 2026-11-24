# Testes — Sprint 64

## Critérios

- política aceita lista vazia e normaliza dias válidos sem duplicidade;
- obrigação concluída exige evidência e dispensa exige justificativa;
- o sino aponta obrigação vencida e a vencer no escopo autorizado;
- Auxiliar não recebe obrigação técnica, financeira ou legal.

## Execução local

Data: 24/11/2026.

- testes de política vazia e confirmada, obrigação vencida, notificação e
  isolamento da Auxiliar — aprovados;
- suíte Django integral com PostgreSQL 17 temporário — **794 testes aprovados**
  em 108,099 segundos;
- configuração Django e migrations — aprovadas;
- scanner do repositório — aprovado;
- adaptador MCP — 6 testes aprovados;
- `git diff --check` — aprovado.

Nenhum banco real, sistema oficial, credencial, push ou deploy foi acessado.
