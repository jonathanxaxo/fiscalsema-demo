# Arquivos — Sprint 38

- `contracts/models.py` — unidades, eventos, `ServiceCatalogEntry`, `WorkOrderServiceLine`.
- `contracts/calculations.py` — `calculate_service_units`.
- `contracts/service_catalog.py` (novo) — regras do catálogo, linhas e ciclo.
- `contracts/views_catalog.py` (novo), `contracts/urls.py`, `contracts/views.py`.
- `contracts/forms.py` — formulários do catálogo, da linha e das ações; quantidade bloqueada com linhas.
- Templates novos: `service_catalog_list`, `service_catalog_form`, `work_order_service_line_form`, `_remove`, `_action`.
- `templates/contracts/work_order_detail.html`, `contract_detail.html`, `report.html`.
- `core/static/core/css/app.css` — etiquetas de situação.
- `contracts/migrations/0022_catalogo_servicos_os.py`.
- `contracts/test_catalogo_servicos.py` — 9 testes.
