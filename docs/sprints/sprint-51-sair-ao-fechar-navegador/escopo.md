# Sprint 51 — Sair ao fechar o navegador

## Solicitação

"Quando eu fechar o navegador, o sistema deslogar também." E: "a regra de uma
hora pode deixar para quando ele esquecer o navegador aberto."

## Antes

O cookie de login tinha validade de 2 semanas: fechar e abrir o navegador
mantinha a pessoa logada.

## Agora

- O cookie de login não tem data de validade: ao **fechar o navegador**
  (todas as janelas), o acesso termina e é preciso entrar de novo com a senha.
- Com o **navegador esquecido aberto**, continua valendo a Sprint 49: 1 hora sem
  uso encerra o acesso.
- Vale para todos os perfis. Configurável por `SESSION_EXPIRE_AT_BROWSER_CLOSE`
  (padrão ligado); nenhuma variável nova na Vercel.
- O Arise sabe a regra no nível básico (fechar o navegador encerra; fechar só
  uma aba não; para sair na hora, use Sair).

## Limites conhecidos

- Fechar só uma aba não encerra o acesso (o navegador continua aberto).
- Navegadores configurados para "continuar de onde parou" podem restaurar a
  sessão ao reabrir; nesse caso a regra de 1 hora sem uso continua protegendo.
