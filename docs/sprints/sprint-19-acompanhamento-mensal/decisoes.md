# Decisões da Sprint 19

1. **Regra copiada do sistema principal, sem invenção**: mesmos status, textos
   e prioridade (suspensa > pago > NF > execução > pendente).
2. **Sino só com o que pede ação**: o verde fica apenas no painel.
3. **Migração aditiva**: campo booleano com padrão `False`; nenhuma OS muda de
   comportamento até ser marcada (exceto itens com unidade Mês, que já são
   mensais pela própria unidade).
4. **Caixinhas de marcar**: a regra geral de campos (largura 100 %, 44 px)
   deixava a caixinha gigante; foi criada uma regra própria para
   checkbox/radio, que também melhora "Ativo" em itens e empenhos.
5. **Produção**: após o merge, rodar o workflow `migrate-demo.yml` (mesmo
   procedimento das Sprints 10 e 12).
