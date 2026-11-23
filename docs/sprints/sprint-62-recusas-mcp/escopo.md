# Sprint 62 — Recusas do MCP comprovadas e mensagem de recusa clara

## História de usuário

- **COMO:** fiscal que usa uma IA externa conectada pelo MCP;
- **QUERO:** ter certeza de que uma proposta não é executada se eu perder o acesso,
  e ler a recusa em uma frase clara;
- **PARA:** confiar no controle humano e entender por que algo não foi gravado.

## Origem

- Relatório da Formação Claude Code (páginas 67 a 71, apontamento P1): demonstrar a
  execução controlada e as recusas, incluindo permissão revogada.
- Gravação da demonstração: a recusa aparecia como
  `Confirmação recusada: ['Esta proposta venceu...']`, com colchetes e na cor verde
  de sucesso.

## Entregas

- testes novos: contrato transferido para outro Fiscal depois do código e conta
  inativada pelo Administrador depois do código → execução recusada, nada gravado,
  proposta continua pendente e a auditoria não expõe o código;
- mensagens de erro das telas de rascunho sem colchetes nem aspas de lista;
- mensagens de erro nas telas de rascunho na cor de alerta (`danger`, `role="alert"`).

## Fora do escopo

- regras de execução, código de uso único, permissões e auditoria: **sem alteração**
  (os testes confirmaram que já recusam corretamente);
- e-mail institucional (SMTP) e login pela rede da SEMA: dependem da infraestrutura
  real e não são necessários para a demonstração.
