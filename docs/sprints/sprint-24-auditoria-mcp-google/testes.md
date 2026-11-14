# Testes e evidências da Sprint 24

Sprint só de documentação e arquitetura; a regressão confirma que nada quebrou.

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **518 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |
| Metodologia | `core.test_metodologia` (dentro da suíte) | lista a Sprint 24 |
| DNS do domínio institucional | consulta pública | não executada: rede da sessão bloqueia DNS (pendência do responsável) |
| `django-oauth-toolkit` 3.4.1 | metadados do PyPI | compatível com Django 5.2 / Python 3.14; 4 dependências transitivas |
