# Decisões — Sprint 58

1. O perfil autenticado determina o painel no backend; a escolha visual não
   concede permissões.
2. Administrador Geral e Fiscal preservam os painéis já existentes para evitar
   regressão nas funções que estavam corretas.
3. A Auxiliar recebe somente metadados administrativos e notificações de
   completude. Valores financeiros, conteúdo operacional e arquivos privados
   não entram no contexto do painel nem no sino de notificações.
4. O Gestor Administrativo usa a carteira institucional já autorizada e o
   motor financeiro existente; classificação gerencial não substitui a
   modalidade de medição ou pagamento.
5. O Gestor do Contrato recebe apenas contratos vinculados por acesso
   `READ_ONLY`; relatórios e gráficos não concedem escrita.
6. Os painéis reutilizam `contracts_visible_to` e `contracts_exportable_by`.
   Nenhuma regra de acesso é duplicada em template.
7. Contratos arquivados continuam excluídos pelos querysets autorizados.
8. A Sprint não cria migration nem altera dados de produção.
