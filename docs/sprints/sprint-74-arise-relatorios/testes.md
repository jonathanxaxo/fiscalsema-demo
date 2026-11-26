# Testes — Sprint 74

## Critérios automatizados (`assistant/test_sugestoes_contrato.py`)

- sem contrato, as sugestões de cada perfil continuam iguais;
- com contrato, perguntas sobre saldo, OS, NF e empenhos;
- a Auxiliar Administrativa não recebe perguntas sobre valores;
- perfil sem perguntas de contrato volta às sugestões gerais;
- destaque do contrato ativo no chat;
- regras de impressão dos relatórios (tabela inteira, sem dica de rolagem,
  cabeçalho repetido);
- relatório gerencial sem a frase de dados fictícios e com o aviso legal.

Durante a sprint, dois testes antigos (`core.test_movimento_sistema` e
`core.test_pulso_vivo`) recusaram o uso de `!important` nas regras novas de
impressão, para preservar o modo "Sem movimento". As regras foram reescritas
com seletores mais específicos e o PDF foi conferido de novo.

## Comandos e resultados (26/11/2026)

```text
python scripts/security/scan_repository.py
PASS | nenhum segredo conhecido, dado real ou artefato proibido encontrado

python -m unittest scripts.test_mcp_server
Ran 6 tests — OK

python manage.py check --settings=core.settings_test
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run --settings=core.settings_test
No changes detected

python manage.py test --settings=core.settings_test --noinput --parallel 4
Ran 836 tests — OK

git diff --check
sem problemas
```

## Conferência manual

- PDF dos relatórios gerado no navegador (modo impressão, paisagem): o
  gerencial passou de 5 para 2 páginas, com as colunas até "Saldo"; o do
  contrato passou de 5 para 3 páginas.
- Chat flutuante antes e depois: com contrato ativo, mostra as quatro
  perguntas sobre o contrato.
- Varredura automática em 14 telas (Fiscal Titular, 1440 e 390 px): 66 links
  internos verificados, nenhum quebrado; nenhuma rolagem horizontal.

## Publicação

- PR #73: CI `django-postgresql` aprovada; merge em 26/11/2026 (commit
  `3428af9`) após aprovação do responsável.
- Sem migration.
- Vercel: deploy de produção `READY` para o commit `3428af9`.
- Conferência em produção: `/healthz` com banco "ok" e nenhum erro de execução
  em 15 minutos.
