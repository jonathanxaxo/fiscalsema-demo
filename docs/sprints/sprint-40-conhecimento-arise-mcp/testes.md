# Testes — Sprint 40 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test assistant.test_conhecimento_sprint40 api_v1.test_mcp_remoto` | OK |
| `python manage.py test --settings=core.settings_test --noinput` | 667 testes OK |

Perguntas verificadas: catálogo com UST, homologar serviço, devolver NF com
valor diferente, prazo da fábrica, dashboard com gráfico mensal e CNPJ com
pontuação — cada uma recebe a seção certa da ajuda.
