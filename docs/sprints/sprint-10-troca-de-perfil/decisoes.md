# Decisões da Sprint 10

1. **Conta Fiscal vinculada, sem senha:** em vez de mudar o perfil da própria
   conta (o modelo proíbe superusuário Fiscal e há mais de 20 regras que
   verificam o perfil), a troca usa uma conta Fiscal ligada. Nenhuma regra de
   permissão existente mudou.
2. **Identificador interno:** o e-mail é único no sistema; a conta Fiscal usa
   o e-mail do administrador com `+fiscal`. O responsável continua entrando
   somente com `admin@exemplo.com.br`.
3. **Troca por sessão** (recomendação aceita implicitamente ao autorizar a
   sprint): sair e entrar de novo volta a Administrador.
4. **Somente uma conta:** o comando recusa criar um segundo vínculo.
5. **Concessão só por fluxo manual** com confirmação `HABILITAR`; o fluxo
   verifica `migrate --check` antes de qualquer alteração.
6. **Segurança da troca:** somente POST com CSRF; a volta exige que a sessão
   indique o administrador e que a conta atual seja exatamente a Fiscal
   vinculada; contas inativas são recusadas.
7. **Celular:** o botão do topo empurrava "Sair" para fora da tela; no celular,
   "Atuar como Fiscal" fica no topo do menu e "Voltar a Administrador" na faixa.
8. **Migration em produção:** a aplicação publicada precisa da migration
   `0008`; o fluxo "Migracao manual" deve ser executado logo após o merge.
9. Numeração: a Sprint 10 anterior (redefinição de senha) foi descartada;
   este número passou a esta entrega.
