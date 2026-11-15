# Arquivos — Sprint 39

- `contracts/models.py` — `Invoice.objects.active()`, serviços, substituição, devolução, valor dimensionado; situação de faturamento do serviço.
- `contracts/services.py` — somas só com NF ativas, vínculos, devolução, bloqueios.
- `contracts/accountability.py`, `contracts/dashboard.py`, `contracts/executive_dashboard.py` — NF devolvida fora dos cálculos; avisos de faturamento.
- `core/notifications.py` — avisos no sino.
- `contracts/forms.py` — campos da NF e formulário de devolução.
- `contracts/views.py`, `contracts/views_catalog.py`, `contracts/urls.py` — tela de devolução e detalhes.
- `templates/contracts/invoice_detail.html`, `invoice_return.html` (novo), `work_order_detail.html`.
- `contracts/migrations/0023_nf_servicos_devolucao.py`.
- `contracts/test_nf_dimensionada.py` — 6 testes.
