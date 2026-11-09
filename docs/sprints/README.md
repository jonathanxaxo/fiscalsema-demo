# Organização por sprints

Cada sprint deve possuir uma pasta `sprint-NN-nome` com:

- `escopo.md`: objetivo e limites;
- `arquivos.md`: arquivos criados, alterados e removidos;
- `decisoes.md`: decisões e riscos aceitos;
- `testes.md`: comandos e resultados verificáveis.

Correções futuras criam nova sprint; não reescrevem silenciosamente o histórico
documental das entregas anteriores.

## Sprints registradas

- `sprint-01-vercel-minima`: cópia independente, sanitização, adaptação para
  Vercel e validações sem banco;
- `sprint-02-integracao-postgresql`: primeiro commit local e preparação dos
  testes integrais em PostgreSQL exclusivo.
- `sprint-03-governanca-agente`: criação do `CLAUDE.md` com as regras de
  trabalho, segurança e registro para agentes de IA.
- `sprint-04-diagnostico-visual`: execução local com dados fictícios,
  capturas de tela e lista priorizada de melhorias visuais.
- `sprint-05-correcoes-leitura`: tabelas sem quebra de palavras, aviso de
  rolagem, formatação de exercício, quantidades e CNPJ/CPF.
- `sprint-06-identidade-visual`: logotipo, favicon e ícones SVG próprios,
  faixa de demonstração em âmbar e nome FiscalSema nos títulos.
- `sprint-07-padronizacao-telas`: listas operacionais padronizadas, ações do
  contrato no topo, formulários em duas colunas, rascunhos da IA no layout do
  sistema e correção do menu móvel.
- `sprint-08-painel`: prioridades no topo do painel e barra de atalhos.
- `sprint-09-publicacao`: registro do PR nº 3, CI, Preview, merge e
  conferência da produção.
- `sprint-10-troca-de-perfil`: exceção da demo para uma conta Fiscal atuar
  como o Administrador, sem a senha dele, com auditoria.
- `sprint-11-painel-administrador`: tela inicial do Administrador dedicada ao
  controle de acessos.
- `sprint-12-dados-apresentacao`: fluxo manual que preenche um contrato com
  dados fictícios de apresentação.
- `sprint-13-painel-fiscal`: painel profissional do Fiscal e correção das
  datas dos dados fictícios.
- `sprint-14-notificacoes`: sino de notificações no topo, trazido do sistema
  principal e adaptado à demonstração.
- `sprint-15-impressao-relatorio`: botão de impressão/PDF do relatório com
  abertura automática e página em paisagem.
- `sprint-16-padrao-botoes`: padrão único de botões (40/34 px), relatório no
  layout do sistema e conferência de NF com texto legível.
- `sprint-17-workflow-ia-mcp`: API, adaptador MCP, proposta não executada,
  aprovação humana, matriz de autonomia, testes e roteiro de apresentação.
