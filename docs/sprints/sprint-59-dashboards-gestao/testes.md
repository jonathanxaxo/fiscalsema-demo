# Testes — Sprint 59

## Critérios automatizados

- Auxiliar vê somente OS abertas de contratos não arquivados;
- OS com prazo contratual ultrapassado aparece como “Em atraso” no painel e no
  sino;
- documento privado, OS concluída, contrato arquivado e links de detalhe não
  aparecem no painel da Auxiliar;
- filtros por contrato e situação respeitam o queryset autorizado;
- Gestor Administrativo vê a carteira geral e recalcula o dashboard ao
  selecionar um contrato;
- relatório gerencial geral e individual é exclusivo do Gestor Administrativo
  e possui modo de impressão/PDF;
- Gestor do Contrato seleciona entre dois ou mais vínculos e não alcança
  contrato fora do escopo;
- carga de demonstração permanece idempotente com dois vínculos por Gestor do
  Contrato.

## Execução local

Data: 19/11/2026.

- compilação dos módulos Python alterados — aprovada;
- `manage.py check --settings=core.settings_test` com configuração temporária e
  fictícia — aprovado, sem alertas;
- `manage.py makemigrations --check --dry-run` com banco temporário — aprovado,
  sem alterações de modelo;
- carregamento dos quatro templates alterados pelo motor Django — aprovado;
- `git diff --check` — aprovado;
- `python scripts/security/scan_repository.py` — aprovado, sem segredo, dado
  real ou artefato proibido;
- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- a tentativa de executar a suíte com SQLite parou corretamente na migration
  que exige PostgreSQL para proteger a auditoria imutável; nenhum teste da
  aplicação foi executado com banco incompatível;
- suíte Django integral com PostgreSQL — pendente da CI do Pull Request.

Nenhum banco real ou de produção foi acessado.

## CI do Pull Request

- primeira execução do GitHub Actions `44655020163`: 749 testes executados,
  com uma falha em asserção do próprio teste novo; o sino global mostrava
  corretamente um alerta geral mesmo quando a tabela estava filtrada por outro
  contrato;
- o teste foi corrigido para validar diretamente as linhas autorizadas da
  tabela, sem exigir que a notificação geral desapareça;
- GitHub Actions `44655568401`, job `django-postgresql` — aprovado em
  20/11/2026;
- suíte Django integral com PostgreSQL 17 — **749 testes aprovados** em
  108,609 segundos;
- migrations, configuração Django, configuração Vercel sem banco, scanner de
  segurança e 6 testes do adaptador MCP — aprovados na mesma execução;
- Preview externo da Vercel bloqueado porque o autor Git não pertence à equipe
  do projeto Vercel. O bloqueio não executou deploy e não representa falha da
  aplicação.
