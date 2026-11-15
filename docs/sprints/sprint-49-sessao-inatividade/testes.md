# Testes — Sprint 49

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **699 testes OK** |

Novos: `accounts/test_sessao_inatividade.py` (7 testes): padrão de 1 hora; uso
dentro da hora mantém; mais de 1 hora encerra, pede senha, mostra mensagem e
registra auditoria; chat/sinal recebem 401; sinal de uso renova sem alterar
dados; atributos só para quem está logado; 0 desliga.

## Navegador (Playwright, limite de teste de 20 s)

- página parada → foi sozinha para `/conta/entrar/?next=/contratos/4/os/` com a
  mensagem de sessão encerrada;
- mouse e teclado em uso por 60 s (sem enviar formulário) → continuou logado
  e navegou normalmente.
