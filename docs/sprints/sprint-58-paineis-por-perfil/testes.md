# Testes — Sprint 58

## Critérios automatizados

- cada um dos cinco perfis recebe o template de painel correspondente;
- Administrador Geral e Fiscal mantêm as telas atuais;
- Auxiliar vê metadados dos contratos não arquivados, sem valores, arquivos
  privados ou alertas operacionais;
- Gestor Administrativo vê a carteira consolidada, classificações e contratos
  ativos individualmente;
- Gestor do Contrato vê somente o contrato vinculado, indicadores, gráfico e
  atalhos de dashboard e relatório;
- tentativa de selecionar contrato não vinculado retorna `404`;
- troca da conta controladora entre os cinco perfis muda efetivamente o painel;
- migrations, segurança, MCP e suíte Django permanecem aprovados.

## Execução

Data: 19/11/2026.

- `.venv\\Scripts\\python.exe -m compileall -q core accounts contracts organizations documents`
  — aprovado;
- `manage.py check --settings=core.settings_test` — aprovado, sem alertas;
- carregamento dos cinco templates pelo motor Django — aprovado;
- `manage.py makemigrations --check --dry-run --settings=core.settings_test`
  — aprovado, sem alterações de modelo; a tentativa opcional de conferir o
  histórico recebeu o aviso esperado porque não há PostgreSQL local autorizado;
- `python scripts/security/scan_repository.py` — aprovado, sem segredo, dado
  real ou artefato proibido;
- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- `git diff --check` — aprovado.

A suíte Django completa foi executada pela CI com PostgreSQL temporário. Nenhum
banco de produção foi acessado.

## CI do Pull Request

- GitHub Actions `44648170660`, job `django-postgresql` — aprovado em
  19/11/2026;
- suíte Django integral — **748 testes aprovados** em 106,719 segundos;
- adaptador MCP — **6 testes aprovados**;
- migrations, configuração, scanner de segurança e configuração Vercel sem
  banco — aprovados;
- o Preview externo da Vercel não foi criado porque o autor Git local não
  pertence à equipe Vercel. Esse bloqueio de conta não executou deploy e não
  representa falha da aplicação.
