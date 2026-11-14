# Sprint 21 — Assistente IA integrado ao FiscalSema

## Solicitação (versão ajustada pelo responsável)

Assistente de IA nativo do FiscalSema, com a tecnologia de IA já desenvolvida
no projeto de referência da equipe, mas apresentando-se **somente** como
"Assistente IA" do FiscalSema, no menu do sistema.

## Decisões do responsável (por clique)

- conversas anteriores **guardadas no servidor, por usuário** (migração
  autorizada), retenção de 30 dias, botão "Excluir conversa";
- acesso **só pelo menu** "Assistente IA" (sem botão flutuante);
- auditoria e limites na tabela `ApiAccessEvent` da Sprint 17, endpoint
  `/assistente/`;
- Metodologia atualizada a cada sprint (regra no `CLAUDE.md`/`AGENTS.md` e teste).

## Incluído (1ª versão)

- chat em `/assistente/` com streaming, formatação (listas, tabelas, código),
  indicador "digitando", mensagens de erro, nova conversa, conversas
  anteriores e exclusão;
- ajuda de uso do sistema a partir de uma base de conhecimento versionada
  (`assistant/conhecimento/*.md`), adaptada ao perfil ativo;
- cliente de IA em Python puro (formato compatível com OpenAI): Gemini hoje,
  outro provedor compatível só por configuração;
- limites por minuto e por dia, auditoria só de metadados;
- arquitetura preparada (desligada) para consultas futuras a contratos, OS,
  empenhos, prazos, pagamentos e relatórios por serviços internos autorizados.

## Fora do escopo

Consultar dados cadastrados, ler arquivos enviados, executar qualquer ação,
alterar o repositório de referência e as variáveis da Vercel (cadastradas pelo
responsável na publicação).
