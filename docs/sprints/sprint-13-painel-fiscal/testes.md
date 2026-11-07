# Testes e evidências da Sprint 13

| Verificação | Comando | Resultado |
|---|---|---|
| Primeira execução da suíte após o novo layout | `python manage.py test --settings=core.settings_test --noinput` | 445 executados: **falhas esperadas apenas em `core.test_painel_ordem`** (ordem e atalhos da Sprint 08) |
| Testes de layout reescritos | `core.test_painel_ordem` | 3 aprovados |
| Testes de dados fictícios | `contracts.test_seed_demo_presentation` | 7 aprovados (inclui datas futuras → corrigidas, valores preservados) |
| Suíte integral final | mesmo comando | **448 aprovados** |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

## Simulação local (contrato 000885/2026 recriado com dados fictícios)

| Verificação | Resultado |
|---|---|
| Datas históricas no futuro antes da correção | 3 |
| `fix_demo_presentation_dates` | "Datas ... corrigidas com segurança." |
| Datas históricas no futuro depois | 0 |
| Altura do painel (computador) | 4.347 → 2.604 px |
| Altura do painel (iPhone 13) | 7.827 → 4.233 px |
| Rolagem horizontal da página no celular | não |

Capturas antes/depois em `capturas/`.

## Produção

PENDENTE — merge e execução do fluxo "Corrigir datas dos dados ficticios".
