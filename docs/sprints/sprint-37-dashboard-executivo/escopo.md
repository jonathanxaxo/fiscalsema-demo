# Sprint 37 — Dashboard executivo do contrato (referência: FiscalSema Light)

## Autorização

Escolhido por clique ("Dashboard executivo"), com execução em sequência autorizada.

## Incluído

- Novo item **Dashboard** no menu (não aparece para o Administrador, que
  acompanha o sistema e não contratos).
- Página `/contratos/dashboard/` com seletor de contrato (troca automática),
  somente com os contratos que a pessoa já pode ver:
  - indicadores principais (valor atual, empenhado ativo, executado, pago, saldo);
  - **tempo decorrido x execução**: vigência decorrida comparada ao
    comprometido, executado, faturado e pago;
  - **situação das OS** com barras e horas informadas (abertas, entregues no
    ano, gastas informadas);
  - **OS abertas e prazos** com contagem de dias (Sprint 36);
  - consumo por item e posição dos empenhos (mesmo quadro do painel);
  - **evolução mensal** (últimos 12 meses da vigência) de executado, faturado
    e pago, com gráfico e tabela;
  - resumo de NF e pagamentos e aviso de que nada constitui atesto ou
    autorização de pagamento.
- Quadros de itens e empenhos do painel passaram para um arquivo comum
  (`contracts/_posicoes.html`), sem mudar o painel.

Somente leitura; sem migração.
