---
titulo: Prazos da OS, prazo da fábrica e horas gastas
rotas: contracts:work_order_create contracts:work_order_update contracts:work_order_detail contracts:work_order_list
perfis: FISCAL USUARIO_CONSULTA
palavras: prazo prazos contratual fabrica cobrar cobranca atraso atrasada vencida vence faltam dias contagem horas gastas efetivamente entrega seis meses
---
Na OS existem dois prazos:
- **Prazo contratual (abertura + 6 meses)**: sugerido automaticamente ao cadastrar a OS (pode ser alterado). É ele que define se a OS está **em atraso**.
- **Prazo de entrega da fábrica** (opcional): data combinada com a fábrica. O sistema avisa **"Cobrar a fábrica"** 7 dias antes (amarelo) e depois de vencer (vermelho), no sino e na Central de trabalho.
- **Horas efetivamente gastas** (opcional, só OS por hora): informadas pela fábrica na entrega; são **informativas** — a cobrança continua pelas horas da OS. A tela mostra a diferença.
Contagem de dias (OS em aberto): "faltam N dias" (verde; amarelo com 7 dias ou menos), "vence hoje" e "vencido há N dias" (vermelho). Situações: No prazo, Cobrar a fábrica, Em atraso, Entregue, Entregue com atraso, Cancelada.
Onde ver: detalhe e lista de OS, Próximos prazos no Painel, Dashboard e relatório ("Prazos e horas informados nas OS").
