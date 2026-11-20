# Decisões — Sprint 60

1. **Escopo da Auxiliar no Arise:** decidido pelo responsável em 20/11/2026,
   "igual ao painel". A Sprint 58 dizia "sem valores", mas o painel da
   Sprint 59 mostra o valor unitário e o valor das OS abertas. Prevaleceu o
   painel atual: valores das OS, sim; valores financeiros do contrato, não.
2. O Arise reaproveita `build_auxiliary_dashboard`, que usa
   `contracts_visible_to` e `work_orders_visible_to`. Nenhuma consulta ou
   permissão nova foi criada.
3. Contrato arquivado ou inexistente informado à Auxiliar devolve a mesma
   mensagem "Nenhum contrato autorizado", sem dizer se o contrato existe.
4. A lista da Auxiliar fica limitada a 30 contratos e 25 OS, e é reduzida até
   o JSON caber inteiro no limite do bloco `<dados>` (`MAX_DATA_CHARS`), com
   uma observação indicando a limitação. O resumo continua com os totais
   reais.
5. **Formatação em reais:** decidida pelo responsável para todos os perfis.
   Só a apresentação muda: os valores vêm prontos do backend, arredondados
   para centavos (`ROUND_HALF_UP`) e escritos no padrão brasileiro. As
   quantidades e horas continuam no formato original.
6. O snapshot do motor (`contract_intelligence_snapshot`) não foi alterado,
   porque a página de inteligência também o usa; a formatação é feita em
   uma cópia, só no caminho do Arise.
