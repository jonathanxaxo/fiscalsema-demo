# Arquivos da Sprint 10

## Criados

- `accounts/profile_switch.py` — telas de troca e context processor;
- `accounts/migrations/0008_profile_switch_link.py` — tabela do vínculo e
  novos tipos de evento de auditoria;
- `accounts/management/commands/enable_demo_profile_switch.py`;
- `.github/workflows/enable-demo-profile-switch.yml` — fluxo manual;
- `accounts/test_profile_switch.py` — 13 testes;
- documentação e capturas em `docs/sprints/sprint-10-troca-de-perfil/`.

## Alterados

- `accounts/models.py` — modelo `ProfileSwitchLink` e eventos
  `PERFIL_FISCAL` / `PERFIL_ADMIN`;
- `accounts/urls.py` — `perfil/fiscal/` e `perfil/administrador/` (somente POST);
- `core/settings_base.py` — registro do context processor;
- `templates/accounts/base.html` — botões e faixa "atuando como Fiscal";
- `core/static/core/css/app.css` — estilos dos botões e da faixa;
- `docs/operacao/demo.md` — procedimento de habilitação;
- `docs/sprints/README.md` — índice.
