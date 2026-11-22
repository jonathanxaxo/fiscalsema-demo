# Arquivos — Sprint 61

## Criados

- `api_v1/leitura.py` — converte comparação, evidências e resultado do
  rascunho em linhas escritas em português (rótulos dos formulários, reais,
  datas e situação em palavras). Só leitura: não altera o rascunho.
- `api_v1/test_rascunho_legivel.py` — testes da formatação e da tela.
- `docs/sprints/sprint-61-rascunho-legivel/` — escopo, arquivos, decisões e
  testes.

## Alterados

- `api_v1/web_views.py` — `AssistantDraftDetailView` envia ao template as
  linhas legíveis, as fontes e o resultado da conferência.
- `templates/api_v1/draft_detail.html` — tabela da proposta, lista de fontes,
  conferência escrita e JSON recolhido em "Ver dados técnicos".
- `core/static/core/css/app.css` — estilos da tabela legível, da etiqueta
  "campo importante" e da área técnica recolhida.
- `templates/core/metodologia.html` — Sprint 61 na linha do tempo, no
  assistente e nos testes.
- `docs/sprints/README.md` — índice das sprints.
