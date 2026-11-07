# Escopo da Sprint 13 — Painel profissional do Fiscal e correção das datas fictícias

## Pedido

Painel do Fiscal profissional, pouco poluído, de fácil acesso, mostrando tudo
o que um fiscal de contratos precisa. Layout aprovado pelo responsável (por
clique), com correção das datas futuras dos dados fictícios.

## Entregas

| Antes | Depois |
|---|---|
| 12 blocos, pendências espalhadas em 4 blocos | Topo do contrato com barra de ações; 5 indicadores com barra de progresso; uma lista única "Central de trabalho" com contagem e botão de ação por pendência |
| "Situação operacional", "OS por situação", "NF e pagamentos" separados | Dois cartões lado a lado: Ordens de Serviço (situações + próximos prazos) e Notas Fiscais e pagamentos |
| Itens e empenhos em tabelas largas | Tabelas enxutas com barra de consumo/uso |
| Calendário financeiro e fechamentos sempre abertos | Recolhidos em "Mais detalhes" |
| Código técnico "COM_PENDENCIA" | "Pendente de conferência" (e demais rótulos legíveis) |
| 4.347 px (computador) / 7.827 px (celular) | 2.604 px (−40%) / 4.233 px (−46%) |

Correção de dados: execuções, NFs e pagamento fictícios não ficam mais com
datas futuras (comando novo e fluxo manual de correção).

## Limites

- nenhuma informação removida: reorganizada ou recolhida;
- nenhuma regra de cálculo ou permissão alterada;
- painel do Administrador e demais telas não alterados;
- sem migration; sem bibliotecas.
