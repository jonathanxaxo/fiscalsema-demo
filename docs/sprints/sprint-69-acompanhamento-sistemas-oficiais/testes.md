# Testes — Sprint 69

## Critérios

- registro concluído exige referência;
- não aplicabilidade exige justificativa;
- pendência necessária aparece no sino dentro do escopo autorizado;
- carteira fictícia cria SIAG, SIGADOC e PNCP sem duplicar;
- Arise deixa explícito que não existe integração automática.

## Execução local

Data: 24/11/2026.

- testes de referência obrigatória, pendência, notificação, idempotência e
  conhecimento seguro do Arise — aprovados;
- suíte Django integral com PostgreSQL 17 temporário — **794 testes aprovados**
  em 108,099 segundos;
- configuração Django e migrations — aprovadas;
- scanner do repositório — aprovado;
- adaptador MCP — 6 testes aprovados;
- `git diff --check` — aprovado.

Na execução local, nenhum banco institucional, sistema oficial, credencial,
push ou deploy foi acessado.

## CI do Pull Request

- Pull Request funcional `#66`, execução `45405280423`, job
  `django-postgresql` — aprovado em 24/11/2026;
- migrations, configuração Django, configuração Vercel sem banco, scanner de
  segurança, 6 testes do adaptador MCP e **794 testes integrais** — aprovados;
- o Preview externo da Vercel foi bloqueado porque o autor Git não pertence à
  equipe do projeto. O bloqueio não executou Preview e não representa falha da
  aplicação;
- o Pull Request foi incorporado à `main` por squash no commit `af5c0f9`;
- GitHub Actions da `main`, execução `45405879326`, job
  `django-postgresql` — aprovado.

## Publicação e validação em produção

Data: 24/11/2026.

- Vercel confirmou a conclusão do deploy de produção associado ao commit
  `af5c0f9`;
- GitHub Actions `45405942943` aplicou a migration `0029` no banco exclusivo
  da demonstração e restringiu novamente o usuário de execução;
- GitHub Actions `45406261989` preparou, de forma idempotente, a conta
  `admin@exemplo.com.br`, os cinco perfis e a carteira fictícia;
- o fluxo confirmou uma única conta controladora, cinco perfis e contas
  internas sem senha utilizável;
- `https://fiscalsema-demo.vercel.app/healthz` respondeu HTTP `200` com
  aplicação e banco em estado `ok`;
- a página pública de entrada respondeu HTTP `200` e manteve os avisos
  permanentes de ambiente demonstrativo e dados exclusivamente fictícios;
- as telas autenticadas, permissões e dados próprios dos perfis foram validados
  pela suíte automatizada. A senha da conta não foi acessada;
- nenhum banco institucional nem sistema oficial (SIAG, SIGADOC ou PNCP) foi
  acessado: os registros criados são exclusivamente fictícios e manuais.
