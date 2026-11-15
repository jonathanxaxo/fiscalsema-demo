# Sprint 49 — Sair do sistema após 1 hora sem uso

## Solicitação

"Quando o fiscal ou qualquer outro perfil ficar mais de 1 h sem mexer no
sistema, o perfil sai e ele vai ter que entrar novamente com a sua senha. Não
mude nada do que está funcionando."

## Antes

A sessão seguia o padrão do Django (2 semanas), sem controle de inatividade.

## Agora

- **Servidor** (`IdleSessionTimeoutMiddleware`): cada ação da pessoa logada
  atualiza a hora da última atividade. Passou de 1 hora sem uso → sessão
  encerrada, registro na auditoria (LOGOUT, motivo "inatividade") e volta para
  a entrada com a mensagem "Sua sessão foi encerrada após 1 hora sem uso.
  Entre novamente com a sua senha." Depois de entrar, a pessoa volta para a
  tela em que estava (`?next=`).
- **Navegador**: se a aba ficar parada por 1 hora, a tela vai sozinha para a
  entrada. Enquanto a pessoa digita ou rola a tela sem salvar, o navegador
  avisa o servidor a cada 5 minutos de uso, para não perder o que está sendo
  preenchido. Outra aba aberta e em uso também conta.
- Vale para **todos os perfis**. O chat recebe a mesma mensagem (erro 401).
- Configurável por `SESSION_IDLE_TIMEOUT_SECONDS` (padrão 3600; 0 desliga);
  nenhuma variável nova precisa ser criada na Vercel.

## Fora do escopo

Nenhuma tela, regra, migração ou dependência muda. MCP/OAuth usam tokens
próprios e não são afetados.
