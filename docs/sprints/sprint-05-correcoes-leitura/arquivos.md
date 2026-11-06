# Arquivos da Sprint 05

## Criados

- `core/templatetags/__init__.py`;
- `core/templatetags/formatacao.py` — filtros `quantidade` e `cnpj_cpf`;
- `core/test_formatacao.py` — 5 testes dos filtros;
- documentação e capturas em `docs/sprints/sprint-05-correcoes-leitura/`.

## Alterados

- `core/static/core/css/app.css` — `overflow-wrap: anywhere` → `break-word`;
  estilo do aviso de rolagem;
- `core/static/core/js/app.js` — aviso de rolagem horizontal das tabelas;
- `templates/home.html`, `templates/contracts/{accountability,commitment_detail,commitment_list,report,table_mode}.html` — exercício sem separador de milhar;
- `templates/contracts/{item_detail,item_list,table_mode,work_order_detail,work_order_list}.html` — filtro `quantidade`;
- `templates/contracts/{contract_detail,invoice_detail}.html` — filtro `cnpj_cpf`;
  texto da "Etapa 19" em `contract_detail.html`;
- `contracts/test_financial_engine.py` — expectativa `"100,0000"` atualizada
  para `"100,00"`, conforme o novo formato aprovado;
- `docs/sprints/README.md` — índice.
