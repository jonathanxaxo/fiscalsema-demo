---
titulo: Itens e empenhos
rotas: contracts:item_list contracts:item_detail contracts:item_create contracts:item_update contracts:commitment_list contracts:commitment_detail contracts:commitment_create contracts:commitment_update contracts:commitment_movement_create
perfis: FISCAL USUARIO_CONSULTA
palavras: item itens unidade quantidade valor unitario hora saldo empenho empenhos nota reforco anulacao estorno ped fonte exercicio
---
**Itens** (Contrato → Itens → Cadastrar item): número, descrição, unidade (Hora, Unidade, Mês, Serviço etc.), quantidade contratada e valor unitário. O valor total é calculado. A soma dos itens deve bater com o valor atual do contrato; se divergir, aparece aviso no painel e no sino. Item por hora com saldo abaixo de 20% gera alerta.

**Empenhos** (Contrato → Empenhos → Cadastrar empenho): número, PED, data, valor inicial e fonte. Movimentações: reforço, anulação ou estorno (botão "Registrar reforço, anulação ou estorno" no empenho). O saldo do empenho considera os rateios das OS; abaixo de 20% gera alerta.
