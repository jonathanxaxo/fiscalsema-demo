# Sprint 75 — Criar conta com órgão/setor e senha pelo e-mail

## História de usuário

- **COMO:** visitante do Demo Day ou servidor interessado;
- **QUERO:** criar minha própria conta informando nome, e-mail, órgão e setor
  e receber no e-mail um link para criar a senha;
- **PARA:** usar a demonstração sem depender do responsável para me cadastrar.

## Decisões do responsável (26/11/2026)

- botão de cadastro na tela de login;
- órgão e setor escolhidos na lista ou digitados, ficando disponíveis para os
  próximos;
- link no e-mail para a pessoa criar a própria senha;
- sem aprovação manual;
- perfil Fiscal com consulta (somente leitura) aos contratos fictícios;
- Arise liberado com o limite diário já existente.

## Critérios de aceite

- "Criar conta" na tela de login, ligado por configuração;
- órgão e setor: lista dos ativos ou nome novo, sem duplicar
  (maiúsculas/minúsculas e espaços ignorados);
- conta ativa como Fiscal Titular, **sem senha** até o link do e-mail;
- e-mail com link de uso único e com prazo, sem senha escrita;
- criação da senha pelo link e entrada pelo login normal;
- acesso somente de leitura aos contratos marcados como fictícios, concedido
  pelo fiscal de cada contrato e auditado;
- reenvio do link quando a pessoa repete o cadastro antes de criar a senha;
- recusa de e-mail que já tem conta com senha;
- limite de cadastros por conexão, campo anti-robô e auditoria.

## Fora do escopo

- migração de banco (não foi necessária);
- mudança no cadastro com aprovação, no login Google e no "Esqueci minha senha";
- confirmação por SMS, captcha externo ou aprovação posterior.
