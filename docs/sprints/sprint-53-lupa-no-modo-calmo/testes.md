# Testes — Sprint 53

Resultados a registrar após a execução:

| Comando ou verificação | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | 6 testes OK |
| `python -m compileall -q ...` | OK |
| Validação estática de SVG, HTML, JavaScript e CSS | OK |
| `python manage.py check --settings=core.settings_test` | A executar na CI (ambiente local sem todas as dependências) |
| `python manage.py makemigrations --check --dry-run` | A executar na CI (ambiente local sem todas as dependências) |
| `python manage.py test --settings=core.settings_test --noinput` | A executar na CI (ambiente local sem todas as dependências) |
| Navegador com `prefers-reduced-motion: true`: `Calmo` mantém a lupa animada | PASS — posição da varredura e opacidade do anel mudaram em 900 ms |
| Navegador: arquivo usado por `Sem` permanece parado | PASS — sem estilos ou elementos animados |

Nenhuma dependência foi instalada. A suíte Django integral fica condicionada à
CI do GitHub, que cria o ambiente a partir de `requirements.txt`.
