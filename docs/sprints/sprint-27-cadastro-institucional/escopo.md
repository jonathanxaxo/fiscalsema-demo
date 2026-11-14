# Sprint 27 — Cadastro institucional pelo Google

## Decisão do responsável

Plano aprovado por clique, com PR + merge se os testes passarem.

## Incluído

- Política de novos cadastros por variáveis de ambiente:
  `ALLOWED_SIGNUP_DOMAINS` (domínio institucional inteiro) e
  `ALLOWED_SIGNUP_EMAILS` (exceções exatas, como a do professor — o domínio
  da exceção não é liberado). Sem listas, ninguém se cadastra.
- `GOOGLE_REQUIRE_HOSTED_DOMAIN` (desligado até confirmar o Google Workspace
  do domínio institucional): quando ligado, exige `hd` igual ao domínio.
- "Entrar com Google" sem cadastro + e-mail autorizado → tela "Complete seu
  cadastro" → conta **pendente de aprovação**, solicitação ao Administrador e
  vínculo Google, numa transação; sem senha (entra sempre pelo Google).
- Mesmo perfil solicitado do cadastro atual (convite de consulta → Usuário de
  consulta; demais → Fiscal), sempre pendente; nada de acesso automático.
- A política também vale no formulário de cadastro com senha (desligado na demo).
- Contas existentes não passam pela política (vínculo seguro da Sprint 25).

Sem migração e sem dependência nova.
