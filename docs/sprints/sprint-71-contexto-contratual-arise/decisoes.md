# Decisões — Sprint 71

1. O backend é a fonte de verdade do contrato ativo; o campo enviado pelo
   navegador nunca concede acesso.
2. A resolução usa o mesmo conjunto `contracts_visible_to` das telas do
   sistema e exclui contratos arquivados.
3. A conversa guarda somente a referência opcional ao contrato. Valores,
   documentos e saldos continuam calculados na fonte autorizada.
4. Trocar o contrato cria outra conversa em vez de reaproveitar mensagens do
   contexto anterior. A conversa antiga não é apagada.
5. Sem contrato selecionado, o Arise mantém o comportamento geral permitido
   ao perfil e informa a ausência de contexto específico.
6. A melhoria é somente de leitura e não altera permissões, fórmulas,
   homologação, atesto ou pagamento.
