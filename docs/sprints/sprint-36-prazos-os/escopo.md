# Sprint 36 — Prazos da OS, prazo da fábrica e contagem de dias (referência: FiscalSema Light)

## Autorização

Escolhido por clique ("Prazos da OS e dias"), com execução em sequência
autorizada ("Todas em sequência"), incluindo migração e `migrate-demo`.

## Incluído

- **Prazo contratual** (campo `prazo` existente): rótulo "Prazo contratual
  (abertura + 6 meses)", sugerido ao cadastrar a OS (no servidor e no
  navegador) e editável; é ele que define o atraso.
- **Prazo de entrega da fábrica** (novo, opcional): não pode ser anterior à
  abertura; gera aviso "Cobrar a fábrica" 7 dias antes (amarelo) e depois de
  vencer (vermelho), no sino e na Central de trabalho.
- **Horas efetivamente gastas** (novo, opcional, só OS por hora): informativo,
  não negativo; a cobrança continua pelas horas da OS; mostra a diferença.
- **Contagem de dias**: "faltam N dias" (verde; amarelo com 7 dias ou menos),
  "vence hoje" e "vencido há N dias" (vermelho), só para OS em aberto.
- **Situação do prazo**: No prazo, Cobrar a fábrica, Em atraso há N dias,
  Entregue, Entregue com atraso, Cancelada.
- Telas: detalhe e lista de OS, Próximos prazos e Central de trabalho do
  painel, relatório ("Prazos e horas informados nas OS").
- Auditoria da OS passa a registrar `prazo_fabrica` e `horas_gastas_informadas`.

## Migração

`contracts/0021_os_prazo_fabrica_horas_gastas`: só acrescenta 2 colunas
opcionais; nenhum registro é alterado.
