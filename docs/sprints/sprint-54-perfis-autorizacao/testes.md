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
Uma segunda execução (`44529380727`) confirmou as correções anteriores e
isolou quatro erros em um único import ausente no motor. O merge continuou
bloqueado até a correção.

## Revalidação integral e Preview

- GitHub Actions `44532087566`: aprovado em PostgreSQL 17, com migrations,
  configuração Vercel, varredura de segurança, 6 testes MCP e 733 testes
  Django aprovados;
- Preview Vercel protegido associado ao commit `83c4c71`, com URL registrada
  pelo provedor no PR #51 sem reproduzir identificadores pessoais neste
  repositório;
- homologação da tela de login: HTTP funcional no navegador autenticado,
  título `Entrar — FiscalSema`, aviso permanente de dados fictícios e fontes
  animada/estática do logotipo presentes;
- verificação visual da lupa no modo `Calmo`: duas capturas separadas por
  900 ms produziram quadros diferentes, confirmando que a animação existente
  permaneceu ativa.

## Pendente antes da migração da demo

Antes de aplicar a migração na base da demo, executar
`python manage.py inventory_functional_profiles --details` e registrar a
quantidade e o destino decidido para cada `USUARIO_CONSULTA`.
