# Arquivos da Sprint 18

| Arquivo | Mudança |
|---|---|
| 17 templates em `templates/` (painel, contrato, OS, itens, empenhos, NF, pagamentos, rateio, relatório, prestação de contas, modo tabela, lista de contratos) | `R$ {{` → `R$&nbsp;{{` (121 ocorrências) |
| `core/notifications.py` | valores do sino com espaço que não quebra |
| `core/static/core/css/app.css` | bloco "Sprint 18": valor em uma linha e letra ajustada ao quadro |
| `core/test_valores_sem_quebra.py` | novo: 4 testes |
| `contracts/test_items.py`, `contracts/test_reports.py` | 3 asserções atualizadas para `R$&nbsp;` |
| `docs/sprints/sprint-18-valores-sem-quebra/` | registro desta sprint |
| `docs/sprints/README.md` | índice |
