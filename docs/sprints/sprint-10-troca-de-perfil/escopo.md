# Escopo da Sprint 10 — Troca de perfil Fiscal / Administrador

## História de usuário

- **COMO:** responsável pela demonstração, que usa a conta Fiscal
  `admin@exemplo.com.br` (já cadastrada, com contratos)
- **QUERO:** que essa conta também possa atuar como Administrador, quando eu
  quiser, entrando apenas com o login e a senha que conheço
- **PARA:** administrar a demo sem depender da senha do Administrador inicial,
  que não é conhecida

## Regras de negócio (definidas pelo responsável)

1. Somente essa conta pode trocar de perfil; as demais mantêm o perfil com que
   foram cadastradas.
2. O login e a senha continuam os da conta Fiscal; a senha do Administrador
   não é necessária.

## Critérios de aceite

1. Só a conta habilitada vê o botão; outras contas recebem recusa (403).
2. Atuando como Administrador, menu e permissões são os do Administrador; de
   volta a Fiscal, os de Fiscal.
3. Cada troca gera evento de auditoria.
4. O direito não pode ser concedido por tela, apenas por fluxo manual.
5. Os testes existentes continuam passando.

## Limites

- nenhuma conta é criada e nenhuma senha é alterada;
- a regra "um único Administrador" da demo é mantida;
- nenhuma regra de permissão existente foi alterada;
- exclusivo do ambiente demo; sem bibliotecas novas; sem deploy.

## Histórico

A primeira versão desta sprint (o Administrador atuando como Fiscal) foi
corrigida antes do merge, quando o responsável esclareceu que a conta
principal é a Fiscal e que a senha do Administrador não é conhecida.

## Estado

Implementada e testada; aguardando merge, migration e habilitação.
