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

## Limpar a demonstração

Não use o banco da VM e não importe dumps. Para reiniciar, descarte o banco demo
no provedor autorizado, crie outro banco/role contendo `demo`, reaplique as
migrations e recrie o administrador.

## Arquivos

Uploads de documentos e planilhas permanecem desabilitados. A Vercel limita o
corpo da função a 4,5 MB e não fornece o volume persistente usado pela VM.
