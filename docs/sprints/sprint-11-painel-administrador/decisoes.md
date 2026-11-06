# Decisões da Sprint 11

1. A escolha do painel é feita pelo **perfil da conta em uso**. Na troca de
   perfil (Sprint 10), ao atuar como Administrador a tela inicial passa a ser
   a de acessos; ao voltar a Fiscal, a de contratos.
2. O parâmetro `?contract=` é ignorado para o Administrador: a tela inicial
   dele não exibe contratos.
3. O menu lateral não foi alterado; o Administrador ainda acessa "Contratos"
   pelo menu. Ocultar o menu é outra decisão, não solicitada.
4. Eventos recentes mostram o tipo e o nome da conta; e-mails e endereços de
   origem não são exibidos (a auditoria guarda apenas hashes).
5. A contagem `pending_registration_count` foi mantida, pois o menu e testes
   existentes dependem dela.
