# Testes e evidências da Sprint 11

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `core.test_painel_administrador` | 3 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **440 aprovados** (437 + 3) |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |
| Navegador (Playwright) | Fiscal entra e alterna para Administrador (computador e iPhone 13) | título "Controle de acessos" nos dois |

Casos testados: Administrador vê o painel de acessos sem nenhum contrato
(nem com `?contract=`); Fiscal continua vendo o "Painel do contrato".

Capturas: `capturas/1-painel-fiscal.png`, `2-painel-administrador.png`,
`3-painel-administrador-celular.png`.
