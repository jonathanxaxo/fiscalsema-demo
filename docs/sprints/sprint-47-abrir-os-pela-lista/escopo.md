# Sprint 47 — Abrir a OS pela lista e ações no topo da OS

## Solicitação

"Na aba de ordens de serviço, ao clicar na OS tem que abrir a OS para eu poder
incluir a NOTA FISCAL e editar a OS." Sem desabilitar nenhuma função.

## Diagnóstico

A lista tem 11 colunas e o único link era o botão "Abrir", na última coluna,
que costuma ficar fora da tela (rolagem lateral). O número da OS não era
clicável. Na OS, "Editar OS" ficava só no rodapé.

## Correção (nada foi removido)

- Lista de OS: o número da OS virou link e a linha inteira abre a OS ao
  clicar; o botão "Abrir" continua.
- Modo tabela (OS): número da OS também abre a OS.
- Tela da OS: botões **Cadastrar Nota Fiscal**, **Editar OS** e **Ver notas
  fiscais** logo abaixo do título; os botões da seção de NF e do rodapé continuam.
- As permissões são as mesmas de antes (`can_add_invoice` e `can_edit`).
