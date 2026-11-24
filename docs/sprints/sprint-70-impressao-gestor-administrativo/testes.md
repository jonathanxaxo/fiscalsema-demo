# Testes — Sprint 70

## Critérios

- resposta de impressão do Gestor Administrativo contém o contrato escolhido;
- relatório contratual continua imprimível para Fiscal e Gestor do Contrato
  dentro do escopo autorizado;
- resposta carrega o script de impressão automática;
- script aguarda a remoção de `fs-verificando`;
- script espera uma pintura do navegador antes de imprimir;
- perfis sem permissão continuam bloqueados.

## Execução local

Data: 24/11/2026.

- testes específicos dos painéis por perfil e dos relatórios — **19 testes
  aprovados**;
- suíte Django integral com PostgreSQL 17 temporário e isolado — **795 testes
  aprovados** em 104,976 segundos;
- configuração Django — aprovada, sem alertas;
- verificação de migrations — aprovada, nenhuma alteração detectada;
- scanner do repositório — aprovado, sem segredo, dado real ou artefato
  proibido;
- adaptador MCP — **6 testes aprovados**;
- sintaxe do JavaScript e `git diff --check` — aprovados.

As duas primeiras tentativas de teste não chegaram a executar casos: a
primeira usou o Python global sem Django; a segunda identificou corretamente a
ausência das variáveis descartáveis de teste. A execução válida utilizou a
`.venv` existente, chave fictícia e PostgreSQL temporário, sem instalar
dependência ou acessar banco institucional.

## CI, Pull Request e publicação

- Pull Request funcional `#68`, commit `4c074e9`, execução
  `45462686787`, job `django-postgresql` `138689272347` — aprovado em
  24/11/2026;
- migrations, configuração Django e Vercel, scanner de segurança, 6 testes
  do adaptador MCP e **795 testes integrais** — aprovados;
- o Preview externo da Vercel foi bloqueado porque o autor Git não pertence à
  equipe do projeto. O bloqueio não executou Preview e não representa falha
  da aplicação;
- o Pull Request foi incorporado à `main` por squash no commit `923ed58`;
- GitHub Actions da `main`, execução `45463396156`, job
  `django-postgresql` `138691771480` — aprovado.

## Validação em produção

Data: 24/11/2026.

- Vercel confirmou `Deployment has completed` para o commit `923ed58`;
- `https://fiscalsema-demo.vercel.app/healthz` respondeu HTTP `200`, com
  aplicação e banco em estado `ok`;
- `https://fiscalsema-demo.vercel.app/static/contracts/report_print.js`
  respondeu HTTP `200` e publicou a espera por `fs-verificando`, o
  `MutationObserver` e o `requestAnimationFrame`;
- a página pública de entrada abriu normalmente e preservou os avisos de
  demonstração e dados fictícios;
- a geração visual do PDF autenticado não foi executada pelo agente porque a
  sessão de teste estava encerrada e nenhuma senha foi acessada. O fluxo está
  coberto pelos testes automatizados, mas a conferência visual final deve ser
  feita por uma pessoa autenticada no botão `Imprimir / Salvar PDF`.

Nenhum dado real, senha ou banco institucional foi acessado.
