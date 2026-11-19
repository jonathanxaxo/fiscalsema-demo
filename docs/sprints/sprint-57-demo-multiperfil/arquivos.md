# Arquivos — Sprint 57

| Grupo | Alteração |
|---|---|
| `accounts/models.py` e migration `0012` | Vínculo da conta controladora com os cinco perfis e evento de auditoria |
| `accounts/demo_profiles.py` | Criação protegida das contas internas sem login direto |
| `accounts/profile_switch.py` e `templates/accounts/base.html` | Seletor multiperfil e troca de identidade por sessão |
| `accounts/management/commands/` | Habilitação multiperfil e inventário sem misturar contas internas |
| `accounts/services.py`, `organizations/services.py` | Bloqueio de alterações administrativas diretas nas contas internas |
| `contracts/management/commands/seed_demo_portfolio.py` | Carteira fictícia idempotente para as contas ativas |
| `contracts/management/commands/seed_demo_presentation.py` | Reuso seguro do pacote operacional em mais de um contrato |
| `.github/workflows/prepare-demo-multprofile.yml` | Fluxo manual com confirmação explícita |
| `accounts/test_demo_multprofile.py` | Exclusividade, senha, auditoria, troca e bloqueio do login interno |
| `contracts/test_demo_portfolio.py` | Idempotência, classificações e visibilidade por perfil |
| documentação e Metodologia | Operação, segurança, decisões e evidências |
