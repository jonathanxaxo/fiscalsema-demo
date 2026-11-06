# Escopo da Sprint 10 — Recuperar o acesso do administrador

## Problema

O responsável não lembra a senha da conta administrativa da demo, e a
recuperação por e-mail não funciona porque o envio de e-mails está desativado
no ambiente demo.

## Objetivo

Permitir redefinir a senha do Administrador existente por um fluxo manual,
auditado e sem expor a senha, mantendo o mesmo login.

## Entregas

- comando `reset_demo_admin_password`;
- fluxo manual `.github/workflows/reset-demo-admin-password.yml`;
- testes e instruções em `docs/operacao/demo.md`.

## Limites

- não cria contas e não altera login, perfil ou permissões;
- a regra "somente uma conta administrativa" continua valendo;
- a senha é informada somente pelo responsável, como secret do GitHub;
- o agente não executa o fluxo nem acessa o banco de produção;
- a alternância de perfil Administrador/Fiscal é a Sprint 11, ainda não
  autorizada.

## Estado

Implementada; aguardando PR, merge e execução do fluxo pelo responsável.
