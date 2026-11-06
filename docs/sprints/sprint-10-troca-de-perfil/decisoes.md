# Decisões da Sprint 10

1. **Vínculo entre duas contas existentes:** a conta Fiscal do responsável é
   ligada ao único Administrador da demo. A troca não muda o perfil de
   nenhuma conta; o sistema passa a usar a outra conta na sessão. Assim
   nenhuma regra de permissão existente mudou e o requisito "um único
   Administrador" é mantido.
2. **Sem senha do Administrador:** a troca não pede a senha da outra conta.
   Decisão consciente do responsável: quem souber a senha da conta Fiscal
   habilitada terá os poderes do Administrador.
3. **Administrador encontrado automaticamente:** o fluxo usa o único
   Administrador ativo; se houver mais de um, exige o e-mail.
4. **Troca por sessão:** sair e entrar de novo começa como Fiscal.
5. **Somente um vínculo** no sistema; o comando recusa um segundo.
6. **Concessão só por fluxo manual** com confirmação `HABILITAR` e
   `migrate --check`.
7. **Segurança da troca:** somente POST com CSRF; a volta exige que a sessão
   registre a conta de origem e que as duas contas sejam as do vínculo;
   contas inativas são recusadas.
8. **Auditoria:** os eventos de troca são registrados em nome da conta Fiscal
   de origem, com os identificadores das duas contas. A criação do vínculo é
   rastreada pela execução do fluxo no GitHub Actions e pela data no próprio
   vínculo.
9. **Celular:** o botão do topo empurrava "Sair" para fora da tela; no
   celular, a troca fica no topo do menu e o retorno na faixa azul.
10. **Migration em produção:** executar o fluxo "Migracao manual" logo após o
    merge.
11. **Correção de rumo:** a primeira implementação partia do Administrador e
    criava uma conta Fiscal interna; foi substituída antes do merge.
