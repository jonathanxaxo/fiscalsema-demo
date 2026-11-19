# Testes — Sprint 54

## Executados localmente

- `python -m compileall -q accounts assistant audit contracts core documents organizations`
  — aprovado;
- `python manage.py check --settings=core.settings_test` — aprovado, sem
  problemas;
- `python manage.py makemigrations --check --dry-run --settings=core.settings_test`
  — aprovado, nenhuma migração pendente;
- `python manage.py test accounts.test_functional_profiles
  contracts.test_profiles_intelligence.IntelligencePureUnitTests
  --settings=core.settings_test --noinput` — 6 testes aprovados;
- `git diff --check` — aprovado.

## Pendente antes da publicação

A suíte Django integrada depende de PostgreSQL. O banco local configurado não
está disponível para esta execução; por isso, a validação integral deverá ser
executada pela CI com o serviço PostgreSQL antes de qualquer merge/deploy.
Essa suíte inclui os testes integrados de perfis da interface e da API,
revogação dinâmica de vínculo, substituição vencida, metadados sem conteúdo
privado e bloqueio de rascunho para perfis somente leitura.

Antes de aplicar a migração na base da demo, executar
`python manage.py inventory_functional_profiles --details` e registrar a
quantidade e o destino decidido para cada `USUARIO_CONSULTA`.
