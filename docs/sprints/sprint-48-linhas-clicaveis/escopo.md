# Sprint 48 — Clicar na linha abre o registro no sistema inteiro

## Solicitação

"Colocar esse link [da Sprint 47] no sistema inteiro, para clicar sem precisar
do botão Abrir. Verificar o sistema inteiro; não alterar visual nem nada que já
funciona."

## Verificação (varredura com Playwright, dados fictícios)

| Tela | Linha abre |
|---|---|
| Painel: OS, NF e pagamentos, itens, empenhos, prazo da NF | OS / NF / item / empenho |
| Dashboard executivo: OS abertas, itens, empenhos | OS / item / empenho |
| Contratos | cadastro do contrato |
| Itens / Empenhos / Ordens de serviço | item / empenho / OS |
| Prestação de contas | empenho / OS / NF / pagamento |
| Modo tabela (itens, OS, rateios, empenhos, NF) | item / OS / OS / empenho / NF |
| Dentro da OS: notas fiscais | NF |
| Dentro da NF: pagamentos | pagamento |
| Dentro do empenho: rateios | OS |
| Rascunhos da IA | revisão do rascunho |
| Solicitações de cadastro e importações | revisão / detalhe da importação |

## Ficaram de fora (de propósito)

Tabelas cujo único link faz uma ação e não "abre" um registro: Restaurar
(arquivados), Baixar (documentos), Editar/Inativar (organizações, setores,
usuários), revogar acessos, catálogo (só Editar), auditoria, relatório para
impressão e tabelas dentro do chat.

## Como funciona

- Regra geral: se o primeiro campo da linha já é um link, a linha abre esse link.
- Nas listas em que o link ficava só na coluna "Ação", a linha recebeu o
  destino de "Abrir" (`data-row-link`).
- Botões, links e formulários dentro da linha continuam funcionando como antes;
  Ctrl/⌘ + clique abre em nova aba. Nenhum botão foi removido.
