# Testes — Sprint 32 (2026-11-15)

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py check --settings=core.settings_test` | sem problemas |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test assistant` | 54 testes OK |
| `python manage.py test --settings=core.settings_test --noinput` | 630 testes OK |

Testes novos (15): leitura de PDF e DOCX; tipo real x extensão; limites de
tamanho, páginas e texto; PDF sem texto; DOCX com XXE, bomba de ZIP e
arquivos corrompidos; nome do arquivo saneado; resposta com `<documento>` e
nada guardado (conversa, auditoria, Document); upload de ~2,7 MB sem
arquivo temporário; documento só naquela pergunta; arquivo recusado com
mensagem clara; pedido grande recusado antes de ler; CSRF mantido; prompt
injection dentro do documento; regra de pedir o anexo; clipe e aviso de LGPD
na tela e no painel flutuante.

Documentos fictícios conferidos: abertos pelo próprio leitor do sistema
(PDF 3 páginas, aviso em todas), visualizados como imagem, sem dados reais.

Capturas: tela cheia no computador (1366×820) e no celular (iPhone 13) com o
arquivo anexado e o aviso de LGPD.
