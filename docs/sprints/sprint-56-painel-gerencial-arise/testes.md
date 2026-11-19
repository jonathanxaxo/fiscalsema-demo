# Testes — Sprint 56

## Executados

- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- checagem estrutural do Django — aprovada;
- checagem de migrações — nenhuma alteração pendente;
- testes puros dos perfis e do motor — 6 aprovados;
- varredura de segredos e dados reais — aprovada;
- compilação Python e `git diff --check` — aprovados.

## CI, Preview e produção

- PR #51: GitHub Actions `44533805848` aprovado, com migrations,
  configuração Vercel, segurança, MCP e 733 testes Django em PostgreSQL 17;
- `main`: GitHub Actions `44534664793` aprovado para o merge `44f5803`;
- Preview protegido da Vercel aprovado no PR, sem registrar identificadores
  pessoais da URL no repositório;
- migration manual `44534847543` aprovada: `accounts.0010/0011` e
  `contracts.0024` a `0028` aplicadas, seguida da restrição do usuário de
  execução;
- produção: `https://fiscalsema-demo.vercel.app/conta/entrar/`, com título de
  login, aviso permanente de dados fictícios e arquivos do logotipo corretos;
- lupa validada em produção no modo `Calmo`: duas capturas separadas por
  900 ms produziram quadros diferentes, confirmando a animação ativa.

## Homologação humana complementar

- percorrer visualmente os cinco perfis com contas fictícias individuais;
- emitir relatórios autenticados de Gestor do Contrato e Gestor
  Administrativo;
- inventariar eventuais contas legadas `USUARIO_CONSULTA` antes de decidir a
  reclassificação individual. A migration não excluiu nem reclassificou essas
  contas automaticamente.
