# Testes — Sprint 63

## Critérios

- a linha do tempo ordena fatos do contrato sem expor detalhes internos;
- perfis veem somente contratos autorizados;
- resumo usa valor e vigência atuais sem alterar o cadastro original;
- registros financeiros existentes continuam com os mesmos cálculos.

## Execução local

Data: 24/11/2026.

- 40 testes direcionados de governança, carteira, dashboards, notificações,
  Arise e Metodologia — aprovados;
- suíte Django integral com PostgreSQL 17 temporário — **794 testes aprovados**
  em 108,099 segundos;
- `manage.py check` — aprovado, sem alertas;
- `manage.py makemigrations --check --dry-run` — aprovado, sem migration pendente;
- scanner do repositório — aprovado, sem segredo, dado real ou artefato proibido;
- adaptador MCP — 6 testes aprovados;
- `git diff --check` — aprovado.

Nenhum banco real, sistema oficial, credencial, push ou deploy foi acessado.
