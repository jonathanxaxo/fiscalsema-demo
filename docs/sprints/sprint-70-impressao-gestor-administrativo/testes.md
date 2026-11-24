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

Nenhum push, deploy ou acesso a dado real foi realizado nesta etapa.
