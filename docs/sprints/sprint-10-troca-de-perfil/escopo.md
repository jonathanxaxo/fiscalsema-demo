# Escopo da Sprint 10 — Troca de perfil Administrador / Fiscal

## História de usuário

- **COMO:** administrador da demonstração (conta `admin@exemplo.com.br`)
- **QUERO:** alternar entre Administrador e Fiscal quando quiser, com o mesmo
  login e senha
- **PARA:** usar as duas visões do sistema sem outra conta

## Regras de negócio (definidas pelo responsável)

1. Somente essa conta pode trocar de perfil; as demais mantêm o perfil com que
   foram cadastradas.
2. Como Fiscal, a conta usa a organização **SEMA** e o nome **Admin**.
3. O login e a senha continuam os mesmos.

## Critérios de aceite

1. Só a conta habilitada vê o botão; outras contas recebem recusa (403).
2. Atuando como Fiscal, menu e permissões são exatamente os de Fiscal.
3. Cada troca gera evento de auditoria.
4. O direito não pode ser concedido por tela, apenas por fluxo manual.
5. Os testes existentes continuam passando.

## Limites

- nenhuma regra de permissão existente foi alterada;
- exclusivo do ambiente demo;
- sem bibliotecas novas; sem deploy.

## Estado

Implementada e testada; aguardando PR, merge, migration e habilitação pelo
responsável.
