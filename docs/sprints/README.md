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
- `sprint-18-valores-sem-quebra`: "R$" nunca separado do número; quadros com
  o valor em uma linha e do mesmo tamanho.
- `sprint-19-acompanhamento-mensal`: OS com acompanhamento mensal no painel,
  no sino, na lista e no detalhe; migração aditiva.
- `sprint-20-metodologia-visual-compacto`: página "Metodologia" para todos os
  usuários logados e botões/menu compactos (32/28 px).
- `sprint-21-assistente-ia`: Assistente IA nativo (ajuda de uso do sistema),
  conversas por usuário, limites e auditoria de metadados.

- `sprint-22-chat-ia-completo`: correção do limite de 2 caracteres na pergunta
  e Assistente IA como chat de IA completo.

- `sprint-23-arise-flutuante`: nome Assistente Arise, ícone e painel
  flutuante em todas as telas e metodologia da construção da IA.

- `sprint-24-auditoria-mcp-google`: diagnóstico e arquitetura do MCP
  bidirecional e do login Google institucional (sem código de produção).

- `sprint-25-login-google`: login com Google (OIDC próprio), vínculo
  seguro a cadastro existente e Minha conta.

- `sprint-26-email-redefinicao-senha`: envio real do e-mail de redefinição
  de senha (Gmail/SMTP) e fluxo manual de senha temporária.

- `sprint-27-cadastro-institucional`: cadastro pelo Google para domínio
  institucional e exceção individual, sempre pendente de aprovação.

- `sprint-28-mcp-identidade`: MCP remoto por identidade com OAuth 2.1
  (PKCE, escopos, consentimento, auditoria e revogação em Minha conta).

- `sprint-29-mcp-analise`: novas consultas no MCP e análise de divergências
  entre documento e sistema, sempre sem gravar.

- `sprint-30-execucao-autorizada`: execução de propostas pelo MCP somente com
  código de uso único gerado pela pessoa logada; pagamento nunca pela IA.

- `sprint-31-mcp-homologacao`: testes de ataque e compatibilidade do MCP/OAuth,
  guia de conexão, roteiro de homologação e ajuda no Assistente Arise.

- `sprint-32-arise-ler-descartar`: Arise lê TR e contrato anexados só em
  memória (ler e descartar) e documentos fictícios para a apresentação.

- `sprint-33-aviso-arise-temporario`: aviso amarelo do painel flutuante do
  Arise some 35 segundos depois de cada abertura.

- `sprint-34-arise-flutuante-arrastavel`: chat flutuante arrastável; minimizar
  mantém a conversa e fechar encerra o chat.

- `sprint-35-formatacao-cnpj`: CPF/CNPJ com máscara e validação, barras
  limitadas e comportamentos de tela (referência: FiscalSema Light).

- `sprint-36-prazos-os`: prazo contratual sugerido, prazo da fábrica, horas
  gastas e contagem de dias (referência: FiscalSema Light).

- `sprint-37-dashboard-executivo`: dashboard executivo do contrato com
  vigência x execução e evolução mensal (referência: FiscalSema Light).

- `sprint-38-catalogo-servicos`: catálogo de serviços (UST/HST/USN), memória
  de cálculo da OS e ciclo entregue/aceito/homologado (referência: FiscalSema Light).

- `sprint-39-nf-dimensionada`: NF ligada aos serviços homologados, valor
  dimensionado e devolução da NF (referência: FiscalSema Light).

- `sprint-40-conhecimento-arise-mcp`: Arise e IA externa (MCP) passam a
  conhecer as funções das Sprints 35 a 39.

- `sprint-41-visual-vivo`: visual vivo em todas as telas, novo logotipo
  (lupa que confere) e controle de movimento.

- `sprint-42-chat-limpo-telas-vivas`: chat flutuante e chat do menu mais
  limpos e vivos, avisos do chat por 10 segundos e telas restantes vivas.

- `sprint-43-nf-em-os-com-catalogo`: botão de cadastrar NF visível na OS com
  serviços do catálogo e atalho a partir do serviço homologado.

- `sprint-44-pulso-vivo`: pulso vivo bem visível em todas as telas, menu,
  situações, Metodologia e ícone flutuante do Arise.

- `sprint-45-movimento-sempre-vivo`: sistema continua vivo quando o
  computador pede menos movimento (vira "Calmo") e mais efeitos vivos.

- `sprint-46-lupa-escaneando`: lupa do logotipo com varredura, brilho e pulso
  sincronizados; parada com "reduzir movimento" e no modo "Sem".

- `sprint-47-abrir-os-pela-lista`: clicar na OS da lista abre a OS; Cadastrar
  Nota Fiscal e Editar OS no topo da OS.
