# Escopo da Sprint 16 — Padrão único de botões

## Pedido

"Melhore todos os botões do sistema; coloque todos no padrão" (print do
relatório com botões de tamanhos diferentes e "Limpar" como link solto).

## Diagnóstico (medição no navegador)

- relatório: única tela fora do layout padrão, com estilos próprios — botões
  de 37 px/13 px ao lado de 42 px/16 px;
- prestação de contas: filtros em coluna única; ações de rodapé como links
  separados por "·";
- quatro alturas diferentes no sistema (46, 39, 35 e 34 px);
- códigos técnicos de conferência de NF (`COM_PENDENCIA`, `CONFERIDA`) no
  relatório, na prestação de contas e na NF.

## Entrega

- dois tamanhos em todo o sistema: **normal 40 px** e **pequeno 34 px**, mesma
  fonte; tipos: principal (verde), secundário (branco com borda), perigo e
  discreto ("Limpar filtros");
- relatório passa a usar o layout padrão (menu, logotipo, sino), mantendo a
  impressão automática em paisagem;
- ações de rodapé e barras do topo viram botões secundários, sem "·";
- filtros da prestação de contas em grade (4/2/1 colunas);
- abas do modo tabela no mesmo estilo;
- conferência de NF com texto legível em etiqueta colorida.

## Limites

- sem mudança de regras, cálculos, permissões ou banco; tela de login mantém
  links (estilo de botão só nas telas internas).
