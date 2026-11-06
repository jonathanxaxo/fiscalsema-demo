# Testes e evidências da Sprint 10

| Verificação | Comando | Resultado |
|---|---|---|
| Testes da troca de perfil | `python manage.py test accounts.test_profile_switch --settings=core.settings_test` | **13 aprovados** |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **437 aprovados** (424 + 13) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma pendente além da `0008` |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## Histórico de execução

- Primeira versão: os testes do comando falharam (`AttributeError`) porque o
  gerenciador exigia senha para a conta interna; corrigido.
- No celular, o botão do topo empurrava "Sair" para fora da tela; corrigido.
- Versão final (conta Fiscal → Administrador): 13 aprovados; 437 na suíte.

## Simulação local (PostgreSQL descartável, dados fictícios)

| Etapa | Resultado |
|---|---|
| `migrate` | `Applying accounts.0008_profile_switch_link... OK` |
| `enable_demo_profile_switch` só com o e-mail da conta Fiscal | "Troca de perfil habilitada com segurança." |
| Verificação do fluxo | `PASS | Troca de perfil exclusiva de uma conta Fiscal e auditavel` |

## Navegador (Playwright), entrando apenas com a senha da conta Fiscal

| Cenário | Computador | Celular (iPhone 13) |
|---|---|---|
| Como Fiscal → área de usuários | 403 | 403 |
| Atuando como Administrador → área de usuários | 200 | 200 |
| De volta a Fiscal → área de usuários | 403 | 403 |
| De volta a Fiscal → cadastrar contrato | 200 | 200 |

Capturas em `capturas/`.

## Produção

PENDENTE — merge, migration e habilitação pelo responsável.
