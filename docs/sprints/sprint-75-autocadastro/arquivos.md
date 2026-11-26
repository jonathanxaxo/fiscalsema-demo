# Arquivos — Sprint 75

## Criados

- `accounts/autocadastro.py` — formulário, criação da conta, órgão/setor,
  consulta aos contratos fictícios, envio do link e limite por conexão;
- `accounts/test_autocadastro.py` — 16 testes;
- `templates/accounts/criar_conta.html`, `criar_conta_enviado.html`,
  `criar_senha.html`, `criar_senha_email.txt` e `criar_senha_assunto.txt`;
- `docs/sprints/sprint-75-autocadastro/` — escopo, decisões, arquivos,
  testes e capturas.

## Alterados

- `accounts/views.py` e `accounts/urls.py` — telas "Criar conta",
  "Confira seu e-mail" e "Criar sua senha";
- `core/settings_base.py`, `core/settings_demo.py` e
  `core/context_processors.py` — `SELF_SIGNUP_ENABLED` e
  `SELF_SIGNUP_LIMIT_PER_HOUR`;
- `templates/accounts/login.html` — botão "Criar conta";
- `core/static/core/css/app.css` — grupos de órgão e setor;
- `docs/seguranca/controles.md`, `templates/core/metodologia.html`,
  `docs/sprints/README.md` e `docs/sprints/sprint-74-arise-relatorios/testes.md`
  — registro.
