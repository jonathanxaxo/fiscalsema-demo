# Decisões da Sprint 16

1. Dois tamanhos apenas (40 e 34 px) em vez de quatro; a hierarquia passa a
   ser dada pela cor (principal/secundário/perigo/discreto), não pelo tamanho.
2. O relatório agora usa o layout do sistema; na impressão, topo, menu e
   botões são ocultados. A faixa "AMBIENTE DE DEMONSTRAÇÃO" permanece no papel
   de propósito, para deixar claro que os dados são fictícios.
3. Teste `test_invoice_checks` passou a verificar "Conferida" (texto legível)
   em vez do código "CONFERIDA" — mudança de exibição aprovada no padrão de
   rótulos legíveis.
4. Estilo de botão nas ações aplicado só a telas internas (`.app-page`): a
   tela de login mantém links.
5. "Status informado" de NF e pagamento é texto livre da fonte e não foi
   traduzido.
