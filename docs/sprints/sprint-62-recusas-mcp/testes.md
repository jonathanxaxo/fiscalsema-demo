# Testes — Sprint 62

## Critérios automatizados (`api_v1/test_permissao_revogada.py`)

- contrato transferido para outro Fiscal depois de gerado o código → `executar_proposta`
  recusada, contrato sem alteração, rascunho pendente, auditoria sem o código;
- conta inativada pelo Administrador (`change_user_status`) depois do código →
  execução recusada, nada gravado, rascunho pendente;
- proposta vencida confirmada pela tela → "Confirmação recusada: Esta proposta venceu."
  sem colchetes, em `class="danger" role="alert"`, rascunho pendente.

## Comandos e resultados

```text
python scripts/security/scan_repository.py                     → PASS
python -m unittest scripts.test_mcp_server                     → 6 testes OK
python manage.py check --settings=core.settings_test           → sem problemas
python manage.py makemigrations --check --dry-run              → sem mudanças
python manage.py test --settings=core.settings_test --noinput  → 782 testes OK
```
