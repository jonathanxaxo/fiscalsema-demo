# Testes — Sprint 42

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run --settings=core.settings_test` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **673 testes OK** |

## Novos testes (`core/test_chat_limpo_telas_vivas.py`)

1. avisos do chat (flutuante e tela cheia) somem em 10 segundos;
2. chat com a camada limpa/viva e respeito aos modos de movimento;
3. telas restantes recebem a camada viva (CSS e sequência no JS).

`assistant/test_anexos.py` passou a exigir `NOTICE_MS = 10000`.

## Validação visual (Playwright, servidor local, dados fictícios)

- chat flutuante aberto e após 10 s (aviso sumiu);
- chat do menu (tela cheia) aberto e após 10 s (aviso sumiu);
- recuperar senha, alterar senha e relatório do contrato com entrada viva;
- auditoria respondeu 403 para o perfil Fiscal (permissão preservada).
