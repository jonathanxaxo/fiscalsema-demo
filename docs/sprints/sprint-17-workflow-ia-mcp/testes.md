# Testes da Sprint 17

## Comandos executados pelo CI

```sh
python manage.py makemigrations --check --dry-run
python manage.py check --settings=core.settings_test
python manage.py check --deploy --settings=core.settings_demo
python manage.py collectstatic --noinput --settings=core.settings_demo
python scripts/security/scan_repository.py
python -m unittest scripts.test_mcp_server
python manage.py test --settings=core.settings_test --noinput --verbosity=1
```

## Resultado verificável

GitHub Actions, workflow **Validação do FiscalSema Demo**, execução nº 30,
run `42627300432`, concluído com sucesso em 09/11/2026.

| Verificação | Resultado |
|---|---|
| Dependências e `pip check` | Aprovado |
| Migrations e configuração | Aprovado; nenhuma migration nova |
| Configuração Vercel sem banco real | Aprovado |
| Scanner de segredos e dados proibidos | Aprovado |
| Testes isolados do adaptador MCP | 6 aprovados |
| Suíte Django em PostgreSQL | 460 aprovados em 54,158 s |
| System check | Nenhum problema identificado |

Os avisos `Forbidden` e as recusas de alteração/exclusão de auditoria vistos
nos logs pertencem a cenários negativos esperados da suíte. O job finalizou
com `success`, comprovando que os bloqueios funcionaram.

## Conclusão

A Sprint 17 preservou as 460 verificações existentes e acrescentou seis testes
específicos para provar que o MCP consulta pela API, cria somente rascunho não
executado e não expõe ferramentas de confirmação ou escrita direta.
