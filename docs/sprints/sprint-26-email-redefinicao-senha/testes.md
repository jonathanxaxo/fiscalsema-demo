# Testes e evidências da Sprint 26

| Verificação | Comando | Resultado |
|---|---|---|
| E-mail e senha temporária | `python manage.py test accounts.test_email_e_senha --settings=core.settings_test --noinput` | 8 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **546 aprovados** |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

Cobertura: e-mail de redefinição enviado com link, saudação e texto sem
"Light"; e-mail desconhecido não envia nada; sem credenciais o envio é
fictício; com credenciais usa SMTP/TLS na porta 587 e remetente correto;
settings da demo usam a função; senha temporária definida com troca
obrigatória, sem alterar perfil/status/organização, limpando bloqueio e
auditando sem a senha; login com a senha temporária leva à troca de senha;
recusas (conta inexistente, senha fraca, ambiente diferente de demo).

Pendente: teste real de envio na Vercel após cadastrar as variáveis.
