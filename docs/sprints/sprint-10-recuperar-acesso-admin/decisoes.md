# Decisões da Sprint 10

1. **Mesmo login:** a conta administrativa existente mantém o e-mail; só a
   senha muda. Criar uma segunda conta administrativa violaria o requisito 5.
2. **Senha somente por secret:** o fluxo lê a senha de
   `FISCALSEMA_DEMO_ADMIN_PASSWORD`, o mesmo secret usado na criação do
   administrador. Não existe campo de senha no formulário do fluxo.
3. **Confirmação explícita:** o fluxo exige digitar `REDEFINIR`.
4. **Somente Administrador ativo e superusuário:** e-mails de Fiscais, de
   contas inativas ou inexistentes são recusados sem alterar nada, e a
   mensagem não revela quais contas existem.
5. **Auditoria sem migração:** reaproveita o evento existente "Senha alterada"
   (`SENHA_ALTERADA`) com `origem = reset_demo_admin_password_env`.
6. **Bloqueio por tentativas:** o fluxo não limpa o bloqueio de login, pois os
   identificadores usam a `DJANGO_SECRET_KEY` da Vercel, diferente da chave
   efêmera do fluxo. O bloqueio expira em 15 minutos.
7. Mesmo grupo de concorrência do fluxo de criação, para nunca executarem ao
   mesmo tempo.
