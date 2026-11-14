---
titulo: Ordens de Serviço e acompanhamento mensal
rotas: contracts:work_order_list contracts:work_order_detail contracts:work_order_create contracts:work_order_update contracts:work_order_cancel contracts:allocation_create contracts:allocation_update contracts:execution_create contracts:execution_update
perfis: FISCAL USUARIO_CONSULTA
palavras: os ordem ordens servico cadastrar prazo status situacao rateio ratear execucao executar medicao mensal mes competencia cancelar assinatura conclusao
---
Caminho: Contrato → Ordens de serviço → Cadastrar OS.
- Informe item, quantidade ou horas, responsável, datas (abertura, assinatura, início, prazo, conclusão), status e processo. O valor unitário é copiado do item.
- Status: Rascunho, Aberta, Assinada, Em execução, Suspensa, Concluída. O cancelamento tem ação própria, com motivo obrigatório.
- **Rateio**: na OS, cadastre o rateio em empenho. OS assinada, em execução ou concluída sem rateio ativo gera alerta.
- **Execução (medição)**: na OS, "Registrar execução" com quantidade, valor, data e competência (MM/AAAA).
- **Acompanhamento mensal**: marque "Exige acompanhamento mensal" no cadastro da OS (itens com unidade Mês entram automaticamente). O painel mostra a competência do mês: vermelho = atualização pendente; amarelo = execução lançada, NF lançada ou OS suspensa; verde = pagamento registrado. O aviso não autoriza pagamento e não substitui Atesto, RAER ou Termo de Homologação.
- Na lista de OS, a etiqueta "Mensal" identifica essas OS.
