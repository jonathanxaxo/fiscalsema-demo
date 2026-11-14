# Sprint 26 — Envio real do e-mail de redefinição de senha e senha temporária

## Problema

O "Esqueci minha senha" não enviava e-mail: a demo forçava o envio fictício
(`EMAIL_BACKEND` dummy), e o link de redefinição era descartado.

## Decisões do responsável (por clique)

- Envio por **Gmail com senha de app** (gratuito; SMTP 587 com TLS);
- **fluxo manual de senha temporária** para recuperar o acesso já;
- PR + merge autorizados se os testes passarem.

## Incluído

- `core/email_config.py`: SMTP ligado só quando `EMAIL_HOST_USER` e
  `EMAIL_HOST_PASSWORD` existem; sem elas, continua fictício.
- E-mail de redefinição revisado (assunto e texto em português, nome
  FiscalSema, aviso de uso único e "ignore se não foi você").
- Comando `set_demo_temporary_password` + workflow manual
  `reset-demo-password.yml` (confirmação `REDEFINIR`; senha vem do segredo
  `FISCALSEMA_DEMO_TEMP_PASSWORD`; troca obrigatória no próximo acesso;
  limpa bloqueio por tentativas; auditoria sem a senha).

Sem migração e sem dependência nova.
