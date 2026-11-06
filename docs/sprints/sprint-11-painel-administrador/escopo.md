# Escopo da Sprint 11 — Painel do Administrador

## História de usuário

- **COMO:** Administrador
- **QUERO:** uma tela inicial voltada ao controle de acessos do sistema
- **PARA:** gerenciar quem acessa o sistema, sem misturar com os contratos,
  que são controle do Fiscal

## Decisão do responsável

Tela inicial do Administrador: **somente controle de acessos** (opção
escolhida entre três). O painel do Fiscal permanece igual.

## Entregas

| Bloco | Conteúdo |
|---|---|
| Solicitações de cadastro | quantidade pendente e as 5 mais antigas, com botão "Analisar" |
| Usuários do sistema | contas por situação, excluídas logicamente e ativas por perfil |
| Acessos recentes | falhas de login em 24 h, logins bloqueados agora, últimos 8 eventos de autenticação |
| Organizações | organizações cadastradas e ativas, setores |
| Ações administrativas | atalhos para Criar Fiscal, Solicitações, Usuários e Auditoria |

## Limites

- somente leitura: nenhuma regra de permissão ou dado foi alterado;
- o menu lateral do Administrador não mudou (o link "Contratos" continua);
- sem bibliotecas; sem migration; sem deploy.

## Estado

Implementada e testada; aguardando PR e merge.
