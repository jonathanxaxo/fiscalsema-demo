# Testes — Sprint 44

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **679 testes OK** |

Novos: `core/test_pulso_vivo.py` (camada cobre telas e ícone; modo "Sem"
continua vencendo). Validação visual com Playwright (dados fictícios):
Painel, Dashboard, Contratos, Rascunhos da IA, Arise, Metodologia e ícone
flutuante, além de vídeo do percurso.
