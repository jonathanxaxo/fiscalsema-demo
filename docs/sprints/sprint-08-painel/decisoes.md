# Decisões da Sprint 08

1. Ordem proposta e aprovada pelo usuário antes da implementação.
2. A resposta "sim" foi interpretada como aprovação também da barra de
   atalhos (opcional). Para removê-la, basta apagar o bloco
   `<nav class="dashboard-shortcuts">` em `templates/home.html`.
3. A barra fica fixa abaixo do cabeçalho ao rolar a página e usa links
   internos (`#id`) para títulos já existentes; nenhum id novo foi criado.
4. A margem de rolagem (`scroll-margin-top: 185px`) foi ajustada após teste no
   navegador, para que o rótulo e o título da seção não fiquem atrás da barra.
5. Conferido por comparação de linhas que o conteúdo do painel é o mesmo,
   apenas reordenado (única diferença: as 3 linhas da barra de atalhos).
