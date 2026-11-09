# Testes da Sprint 17

## Comandos obrigatórios

```sh
python scripts/security/scan_repository.py
python -m unittest scripts.test_mcp_server
python manage.py check --settings=core.settings_test
python manage.py makemigrations --check --dry-run
python manage.py test --settings=core.settings_test --noinput
```

## Evidências esperadas

- scanner sem conteúdo proibido ou segredo;
- seis testes isolados do MCP aprovados;
- `manage.py check` sem erro;
- nenhuma migration nova;
- suíte Django integral aprovada em PostgreSQL pelo CI.

## Limite da evidência

A criação dos arquivos pelo GitHub não executa comandos no repositório. Os
resultados somente devem ser marcados como aprovados depois de execução real
local ou pelo GitHub Actions. Até lá, esta seção não afirma aprovação.
