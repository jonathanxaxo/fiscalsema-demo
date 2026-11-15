# Testes — Sprint 29 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test api_v1.test_mcp_remoto` | 27 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 586 testes OK |

Novos testes: ferramentas listadas como somente leitura; consultas novas
respondem e pagamentos trazem o aviso; análise compara sem gravar (contrato
inalterado, nenhum rascunho, auditoria sem os valores); campos desconhecidos,
análise vazia e outra pessoa são recusados; "meus rascunhos" mostra só os
próprios; normalização de formatos brasileiros.
