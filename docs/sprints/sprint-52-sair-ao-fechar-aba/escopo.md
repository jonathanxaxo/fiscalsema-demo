# Sprint 52 — Fechou a aba do sistema e abriu de novo: pede a senha

## Solicitação

"Não tem como fazer com que ele feche e, assim que abrir de novo, pedir para
digitar a senha?" (fechando só a aba, com o navegador aberto).

## Como funciona

- Cada aba do sistema guarda uma marca (`sessionStorage`), que o navegador
  apaga quando a aba é fechada e mantém ao atualizar ou trocar de tela.
- Ao abrir uma aba sem a marca, ela pergunta às outras abas do sistema
  (`BroadcastChannel`) se alguma está aberta.
  - Alguma respondeu (ex.: Ctrl+clique para nova aba) → segue normalmente.
  - Nenhuma respondeu → o sistema foi fechado e reaberto: a sessão é encerrada
    no servidor (POST com CSRF), a saída vai para a auditoria e a tela vai para
    a entrada com "Por segurança, o sistema foi fechado. Entre novamente com a
    sua senha."; depois da senha, volta para a tela pedida.
- Durante a conferência (menos de 1 s), a tela fica escondida para não mostrar
  dados.
- A tela de entrada marca a aba, então o primeiro acesso depois da senha não é
  derrubado.

## Continua valendo

- Sair ao fechar o navegador inteiro (Sprint 51).
- Sair após 1 hora sem uso com o navegador esquecido aberto (Sprint 49).

## Limites conhecidos

- "Reabrir aba fechada" (Ctrl+Shift+T) e a restauração de sessão do navegador
  podem trazer a marca de volta; nesse caso, vale a regra de 1 hora sem uso.
- Navegadores antigos sem `BroadcastChannel` não fazem a conferência (não
  derrubam por engano).
