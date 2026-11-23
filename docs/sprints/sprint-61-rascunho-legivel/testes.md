# Testes — Sprint 61

## Critérios automatizados (`api_v1/test_rascunho_legivel.py`)

- reais no formato brasileiro (`R$ 4.000,00`, `R$ 1.234.567,50`);
- datas em dd/mm/aaaa, quantidades sem casas desnecessárias, vazio como "—"
  e verdadeiro/falso como "Sim"/"Não";
- a tela do rascunho mostra "O que a IA está propondo", o rótulo do campo
  igual ao do formulário, a data em dd/mm/aaaa, a situação "Novo" e as
  fontes com "referência: REF-001";
- "NÃO EXECUTADO" e "Aprovar e executar" continuam na tela;
- o JSON só aparece dentro da área recolhida "Ver dados técnicos";
- depois da aprovação, "Conferência feita pelo sistema" aparece escrita, com
  o saldo do contrato em reais.

## Comandos e resultados

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
Ran 770 tests — OK
```

## Conferência na tela

Servidor local com banco fictício: a IA externa propôs pelo MCP uma execução
na DEMO-OS-03 (20 horas, R$ 4.000,00, 18/11/2026). A tela mostrou a tabela em
português (Quantidade executada, Valor executado, Data da execução — "Novo",
"campo importante"), a fonte "Relatório fictício de execução — referência:
DEMO-OS-03, semana 46" e o código recolhido em "Ver dados técnicos".

## Publicação

- PR #62: CI `django-postgresql` aprovada; merge em 22/11/2026.
- Vercel: deploy de produção `READY` para o commit `c050752`.
- Conferência em produção: `/healthz` com banco "ok" e folha de estilos com as classes
  `draft-readable`, `draft-section` e `draft-technical`.
