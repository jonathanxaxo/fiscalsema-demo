# Operação da demo

## Estado inicial

Após as migrations, o banco fica sem usuários, contratos e dados operacionais.
A versão atual não cria dados fictícios automaticamente para respeitar a regra
de manter somente a conta administrativa.

## Criar o administrador

Configure `DEMO_ADMIN_EMAIL`, `DEMO_ADMIN_PASSWORD` e `DEMO_ADMIN_NAME` como
segredos e execute:

```text
python manage.py create_demo_admin
```

O comando recusa a execução se já existir qualquer conta e nunca imprime a
senha.

Para a implantação oficial desta demonstração, o fluxo manual
`.github/workflows/create-demo-admin.yml` recebe o e-mail e o nome somente no
momento da execução, lê a senha exclusivamente do secret temporário
`FISCALSEMA_DEMO_ADMIN_PASSWORD` e confirma que a conta criada é o único
usuário, está ativa, possui perfil Administrador, superusuário e grupo técnico
`ADMINISTRADOR`. Depois da criação confirmada, remova o secret temporário.

## Recuperar a senha do administrador

A recuperação por e-mail não funciona na demo, porque o envio de e-mails está
desativado. Para definir uma nova senha sem expor o valor:

1. No GitHub, crie (ou atualize) o secret temporário
   `FISCALSEMA_DEMO_ADMIN_PASSWORD` com a nova senha, em *Settings → Secrets
   and variables → Actions*. Nunca envie a senha por chat ou e-mail.
2. Em *Actions*, execute manualmente o fluxo
   **"Redefinir senha do administrador do FiscalSema Demo"**
   (`.github/workflows/reset-demo-admin-password.yml`), informando o e-mail
   (login) do Administrador e a palavra `REDEFINIR` como confirmação.
3. O fluxo só altera a senha de um Administrador ativo existente: não cria
   contas, não muda o login e registra o evento "Senha alterada" na auditoria.
   Ao final, confirma que a nova senha autentica.
4. Remova o secret temporário.

Se houver muitas tentativas de login erradas antes, o login fica bloqueado por
15 minutos (`AUTH_LOGIN_BLOCK_SECONDS`); aguarde esse prazo antes de entrar.

## Limpar a demonstração

Não use o banco da VM e não importe dumps. Para reiniciar, descarte o banco demo
no provedor autorizado, crie outro banco/role contendo `demo`, reaplique as
migrations e recrie o administrador.

## Arquivos

Uploads de documentos e planilhas permanecem desabilitados. A Vercel limita o
corpo da função a 4,5 MB e não fornece o volume persistente usado pela VM.
