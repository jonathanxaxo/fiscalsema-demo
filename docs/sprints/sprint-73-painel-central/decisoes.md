# Decisões — Sprint 73

1. **Definições tiradas do código.** Os textos seguem
   `contract_financial_position` e `calculate_contract_financial_position`:
   - contratado = valor original mais as alterações vigentes;
   - empenhado = empenhos ativos, com reforços e anulações;
   - comprometido = OS assinadas, em execução ou concluídas;
   - executado = execuções das OS;
   - faturado = valor bruto das NF ativas;
   - pago = pagamentos registrados;
   - saldo = contratado menos comprometido.
2. **Urgência sem regra nova.** `urgent_count` soma somente o que a Central já
   mostrava em vermelho: vigência encerrada, OS vencida, prazo da fábrica
   vencido e NF divergente. `warning_count` é o restante de
   `attention_count`. A ordem da lista não mudou: ela já ia do mais urgente
   para o menos urgente.
3. **Rótulo escrito.** "Urgente" e "Atenção" aparecem como texto, não só
   como cor, para leitura e acessibilidade.
4. **Atalho de Auditoria.** Aparece só quando
   `contracts_with_access_management_visible_to` permite, que é o mesmo
   critério da tela de auditoria do contrato. Nenhuma permissão foi ampliada.
5. **Atalho do Arise.** Usa `?contract=`, já validado no backend desde a
   Sprint 71.
6. **Celular.** Em telas de até 480 px, os indicadores ficam em uma coluna,
   para o valor aparecer inteiro.
