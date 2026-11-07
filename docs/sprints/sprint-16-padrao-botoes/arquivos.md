# Arquivos da Sprint 16

## Criados

- `core/test_padrao_botoes.py` — 4 testes;
- documentação e capturas em `docs/sprints/sprint-16-padrao-botoes/`.

## Alterados

- `core/static/core/css/app.css` — tamanhos padrão, `.toolbar`, ações de
  rodapé, `.button-link-quiet`, `.filter-grid`, estilos do relatório;
- `contracts/static/contracts/table_mode.css` — abas e botão "Aplicar";
- `templates/contracts/report.html` — passa a estender `accounts/base.html`;
- `contracts/static/contracts/report_print.js` — marcador `[data-auto-print]`;
- `core/templatetags/formatacao.py` — filtros `status_conferencia` e `tom_conferencia`;
- `templates/contracts/{accountability,invoice_detail}.html` — rótulos legíveis; filtros em grade;
- 14 templates com ações separadas por "·" (rodapés e barras do topo);
- `contracts/test_reports.py` e `contracts/test_invoice_checks.py` — expectativas
  atualizadas para o novo marcador e o texto "Conferida";
- `docs/sprints/README.md` — índice.
