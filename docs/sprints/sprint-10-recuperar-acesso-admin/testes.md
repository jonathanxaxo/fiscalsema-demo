# Testes e evidências da Sprint 10

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test accounts.test_reset_demo_admin --settings=core.settings_test` | **7 aprovados** |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **431 aprovados** (424 + 7) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## Casos cobertos pelos testes

- redefine a senha, mantém o login, registra auditoria e não imprime a senha;
- recusa e-mail inexistente e conta Fiscal, sem alterar nada;
- recusa senha fraca e variáveis ausentes;
- recusa execução fora do ambiente demo;
- o fluxo é somente manual e lê a senha apenas do secret.

## Simulação local do fluxo (banco PostgreSQL descartável, dados fictícios)

| Etapa do workflow | Resultado |
|---|---|
| Confirmação `REDEFINIR` | aceita; outro valor recusado |
| `reset_demo_admin_password` | "Senha do Administrador demo redefinida com segurança." |
| Verificação de autenticação | `PASS | Administrador autentica com a nova senha` |
| E-mail de Fiscal | recusado: "nenhum Administrador ativo corresponde ao e-mail informado" |

## Execução em produção

PENDENTE — depende do merge e da execução manual pelo responsável.
