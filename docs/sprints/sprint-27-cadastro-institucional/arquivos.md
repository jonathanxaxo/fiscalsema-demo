# Arquivos da Sprint 27

| Arquivo | Mudança |
|---|---|
| `accounts/signup_policy.py` | novo: política de cadastro |
| `accounts/forms.py` | `requested_profile_for` (regra existente extraída), política no cadastro com senha, `GoogleSignupForm` |
| `accounts/google_views.py`, `accounts/urls.py` | etapa "Complete seu cadastro" (`google/cadastro/`) |
| `templates/accounts/google_signup.html` | nova tela |
| `core/settings_base.py`, `.env.example` | `ALLOWED_SIGNUP_DOMAINS`, `ALLOWED_SIGNUP_EMAILS`, `GOOGLE_REQUIRE_HOSTED_DOMAIN` |
| `accounts/test_cadastro_institucional.py` | novo: 13 testes |
| `templates/core/metodologia.html`, `docs/` | Sprint 27 e registro |
