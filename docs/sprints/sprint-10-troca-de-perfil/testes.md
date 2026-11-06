# Testes e evidências da Sprint 10

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test accounts.test_profile_switch --settings=core.settings_test` | **13 aprovados** |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **437 aprovados** (424 + 13) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma pendente além da `0008` criada |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## Primeira execução

Os testes do comando falharam (`AttributeError`) porque o gerenciador de
usuários exige senha válida; a conta Fiscal passou a ser criada diretamente
com senha inutilizável. Depois da correção: 13 aprovados.

## Simulação local da sequência de publicação (PostgreSQL descartável)

| Etapa | Resultado |
|---|---|
| `migrate --check` antes da migration | pendente (esperado) |
| `migrate` | `Applying accounts.0008_profile_switch_link... OK` |
| Confirmação diferente de `HABILITAR` | recusada |
| `enable_demo_profile_switch` | "Troca de perfil habilitada com segurança." |
| Verificação do fluxo | `PASS | Troca de perfil exclusiva, sem senha propria e auditavel` |
| Repetição | "já habilitada; nada foi alterado" |

## Navegador (Playwright)

| Cenário | Computador | Celular (iPhone 13) |
|---|---|---|
| Atuando como Fiscal → cadastrar contrato | 200 | 200 |
| Atuando como Fiscal → usuários (admin) | 403 | 403 |
| De volta a Administrador → usuários | 200 | 200 |
| Botão "Sair" visível | sim | sim (após correção) |

Capturas em `capturas/`.

## Produção

PENDENTE — merge, migration e habilitação pelo responsável.
