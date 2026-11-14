# Arquivos da Sprint 26

| Arquivo | Mudança |
|---|---|
| `core/email_config.py` | novo: configuração SMTP por variáveis de ambiente |
| `core/settings_demo.py` | usa `email_settings(os.environ)` no lugar do e-mail fixo fictício |
| `templates/accounts/password_reset_email.txt`, `password_reset_subject.txt` | texto e assunto revisados |
| `accounts/management/commands/set_demo_temporary_password.py` | novo comando |
| `.github/workflows/reset-demo-password.yml` | novo fluxo manual (autorizado pelo responsável) |
| `accounts/test_email_e_senha.py` | novo: 8 testes |
| `.env.example` | nomes das variáveis de e-mail (senha só na Vercel) |
| `templates/core/metodologia.html`, `docs/` | Sprint 26 e registro |
