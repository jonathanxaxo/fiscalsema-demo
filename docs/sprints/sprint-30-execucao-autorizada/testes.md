# Testes — Sprint 30 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test api_v1.test_mcp_remoto` | 36 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 595 testes OK |

Novos testes: fluxo completo (sem código não executa; código executa uma vez;
repetição devolve "já executada"; código fora da auditoria e do banco);
5 tentativas erradas anulam o código; código vencido e proposta vencida (tela
também respeita); falta do escopo executar e outro cliente de IA; outra pessoa
não gera código nem executa; registro alterado bloqueia; pagamento nunca recebe
código; chave de repetição devolve a mesma proposta; rascunhos da API técnica
inalterados.
