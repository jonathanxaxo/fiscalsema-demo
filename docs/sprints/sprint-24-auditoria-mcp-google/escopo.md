# Sprint 24 — Auditoria e arquitetura: MCP bidirecional e login Google

## Solicitação

Planejar duas evoluções (sem programar código de produção nesta sprint):

1. MCP para consultas, análise de documentos no chat externo e alterações
   mediante autorização autenticada do usuário.
2. Login Google (OpenID Connect) com identificação de cadastros existentes,
   vínculo seguro, cadastro automático de usuários institucionais e exceção
   individual para o professor.

## Decisões do responsável (por clique)

- Sprint 24 autorizada apenas para diagnóstico e decisões;
- login Google com **OpenID Connect próprio, sem dependência**;
- servidor OAuth do MCP com **django-oauth-toolkit** (instalação só na Sprint 27, após nova autorização);
- cadastro com senha **desligado na demo** até existir envio real de e-mail.

## Entregas

- `diagnostico.md`: estado atual de contas, API, MCP, rascunhos e cadastros;
- `decisoes.md`: arquitetura, decisões, riscos e plano das Sprints 25–30;
- Metodologia com a Sprint 24.

Fora do escopo: qualquer código de produção, migração, dependência,
variável na Vercel ou publicação.
