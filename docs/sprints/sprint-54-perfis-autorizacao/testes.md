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
- `python manage.py test
  assistant.test_conhecimento_sprint50.ConhecimentoNovidadesTests
  core.test_valores_sem_quebra.ValoresSemQuebraTemplatesTests
  --settings=core.settings_test --noinput` — 9 testes aprovados;
- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- `python scripts/security/scan_repository.py` — aprovado, sem segredo ou
  dado real conhecido;
- `git diff --check` — aprovado.

## Primeira execução integrada no PR

A execução `44525936327` do GitHub Actions rodou 733 testes e identificou
7 falhas e 3 erros antes do merge. A publicação permaneceu bloqueada. As
causas foram corrigidas no mesmo PR: bloqueio PostgreSQL sem `DISTINCT`,
preservação do vínculo único `READ_ONLY`, compatibilidade do formulário de
compartilhamento, contratos de texto da interface e formatação financeira.
Uma nova execução integral da CI é obrigatória antes do merge.

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
