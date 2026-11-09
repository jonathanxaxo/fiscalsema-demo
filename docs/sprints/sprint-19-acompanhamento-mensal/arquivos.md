# Arquivos da Sprint 19

| Arquivo | Mudança |
|---|---|
| `contracts/models.py` | campo `WorkOrder.monthly_follow_up` (padrão desmarcado) |
| `contracts/migrations/0020_workorder_monthly_follow_up.py` | nova migração: só acrescenta a coluna |
| `contracts/forms.py` | caixinha no cadastro/edição da OS, com texto de ajuda |
| `contracts/services.py` | auditoria da OS registra `acompanhamento_mensal` |
| `contracts/dashboard.py` | cálculo `monthly_work_order_attentions` |
| `core/notifications.py` | avisos vermelhos/amarelos no sino |
| `templates/home.html` | seção "Acompanhamento mensal de OS" |
| `templates/contracts/work_order_list.html` | etiqueta "Mensal" |
| `templates/contracts/work_order_detail.html` | linha "Acompanhamento mensal" |
| `core/static/core/css/app.css` | `.attention-success`; caixinhas de marcar no tamanho certo (antes ocupavam a largura toda) |
| `contracts/test_acompanhamento_mensal.py` | novo: 10 testes |
| `docs/sprints/sprint-19-acompanhamento-mensal/` | registro |
| `docs/sprints/README.md` | índice |
