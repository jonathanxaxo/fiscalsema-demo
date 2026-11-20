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

## Publicação e validação em produção

Data: 20/11/2026.

- Pull Request funcional `#57` incorporado à `main` por squash no commit
  `82d5cb0`;
- GitHub Actions da `main`, execução `44735351811`, job
  `django-postgresql` — aprovado;
- Vercel confirmou a conclusão do deploy associado ao commit publicado;
- `https://fiscalsema-demo.vercel.app/healthz` respondeu HTTP `200` com
  aplicação e banco de dados em estado `ok`;
- a página pública de entrada foi validada no navegador com o aviso permanente
  de ambiente demonstrativo, formulário de autenticação e identidade visual;
- o console público não apresentou erros ou alertas;
- os painéis autenticados e as permissões dos perfis foram validados pela suíte
  automatizada de 749 testes. A senha do usuário não foi acessada durante a
  validação pública;
- GitHub Actions `44737418266` executou com sucesso, na `main` publicada, a
  preparação idempotente da conta `admin@exemplo.com.br` e da carteira
  fictícia: migrations aplicadas foram conferidas, os cinco perfis foram
  habilitados somente para a conta controladora, os dados de demonstração
  foram atualizados e as contas internas permaneceram sem login direto;
- após a preparação, o endpoint público de saúde continuou respondendo HTTP
  `200`, com aplicação e banco de dados em estado `ok`.
