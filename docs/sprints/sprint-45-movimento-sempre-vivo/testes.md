# Testes — Sprint 45

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **682 testes OK** |

Novos: `core/test_movimento_sistema.py` (3 testes).

## Verificação no navegador (Playwright, `reducedMotion`)

| Situação | Modo | Ícone flutuante | Ponto do título | Gráfico | Ícones do menu |
|---|---|---|---|---|---|
| Computador pede menos movimento | calmo | fs-fab | fs-dot | fs-eq | fs-bob |
| Computador sem preferência | vivo | fs-fab | fs-dot | fs-eq | fs-bob |
| Clicou "Sem" | sem | none | — | — | — |
| Clicou "Vivo" (com pedido do computador) | vivo | fs-fab | — | — | — |

Vídeo narrado (pt-BR, legendado) gravado com as telas pulsando; fica fora do
repositório.
