# Testes — Sprint 50

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **705 testes OK** |

Novos (`assistant/test_conhecimento_sprint50.py`, 6 testes):

1. 9 perguntas sobre as novidades encontram a seção certa, nos 3 perfis;
2. respostas básicas presentes (1 hora sem uso, aviso de 10 s, Ctrl+clique);
3. tempo de ociosidade (1 hora) presente em qualquer pergunta, inclusive "Oi, tudo bem?";
4. nenhum arquivo da base tem termo técnico interno;
5. a ajuda sobre sessão não ensina a aumentar ou desligar o tempo;
6. a regra 11 de segurança está no prompt enviado à IA.

Os testes do Arise que já existiam continuam passando (ordem das seções preservada).
