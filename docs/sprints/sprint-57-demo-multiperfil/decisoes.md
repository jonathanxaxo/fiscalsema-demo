# Decisões — Sprint 57

1. A senha permanece somente na conta controladora. Os demais perfis usam
   contas internas com senha inutilizável, impedindo login direto.
2. A troca autentica a sessão na conta interna do perfil. Não foi criada uma
   permissão visual falsa nem uma substituição parcial de `request.user`;
   consultas, grupos e autorizações existentes continuam sendo aplicados.
3. Somente a controladora inicia a troca. Uma conta-alvo aberta diretamente
   não recebe o seletor, ainda que seja o Administrador inicial.
4. O vínculo antigo Fiscal/Administrador é preservado e migrado para o novo
   modelo, reduzindo risco de interrupção durante a evolução.
5. Contas internas não aparecem na administração funcional nem no inventário
   das contas humanas. O inventário informa apenas a quantidade técnica.
6. A carteira é compartilhada por regra de autorização, não duplicada por
   usuário. Fiscais recebem contratos próprios; Gestores do Contrato recebem
   vínculo individual somente leitura; Auxiliar e Gestor Administrativo usam a
   visibilidade institucional já aprovada.
7. A carga é marcada com `[DEMO-CARTEIRA]` e `[DEMO-APRESENTACAO]`, usa apenas
   valores e fornecedores fictícios e é idempotente.
8. Fiscais ativos sem organização ativa fazem o fluxo falhar fechado. O
   comando não muda silenciosamente a organização de uma conta existente.
9. Habilitação e carga só podem rodar no ambiente `demo`, por workflow manual,
   com a confirmação exata `PREPARAR DEMO`.
10. Publicação, migration e execução no banco continuam como etapas separadas.
11. Chaves Django geradas apenas para workflows são mascaradas antes de serem
    gravadas no ambiente da execução; nenhuma chave efêmera deve aparecer nos
    logs de futuras rotinas administrativas.
