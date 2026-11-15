# Arquivos — Sprint 37

- `contracts/executive_dashboard.py` (novo) — vigência, evolução mensal e resumo.
- `contracts/views.py`, `contracts/urls.py` — página e rota.
- `templates/contracts/executive_dashboard.html` (novo), `templates/contracts/_posicoes.html` (novo).
- `templates/home.html` — usa o arquivo comum de posições.
- `templates/accounts/base.html`, `templates/core/icone_menu.html` — item e ícone do menu.
- `core/templatetags/formatacao.py` — filtro `proporcao` para o gráfico.
- `core/static/core/css/app.css` — barras, mini indicadores e gráfico.
- `contracts/test_dashboard_executivo.py` — 4 testes.
