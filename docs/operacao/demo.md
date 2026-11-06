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

## Troca de perfil Fiscal / Administrador (exceção da demo)

Uma única conta Fiscal pode atuar também como o Administrador da demo, sem
precisar da senha do Administrador. As demais contas mantêm o perfil
cadastrado. O direito não pode ser concedido por nenhuma tela; ele é
habilitado uma única vez por fluxo manual:

1. Depois do merge que traz a migration `accounts.0008_profile_switch_link`,
   execute imediatamente o fluxo **"Migracao manual do FiscalSema Demo"**
   (`.github/workflows/migrate-demo.yml`). Até a migration ser aplicada, a
   aplicação publicada pode falhar.
2. Execute o fluxo **"Habilitar troca de perfil do FiscalSema Demo"**
   (`.github/workflows/enable-demo-profile-switch.yml`) informando o e-mail
   (login) da conta Fiscal e a confirmação `HABILITAR`. O e-mail do
   Administrador é opcional: em branco, o fluxo usa o único Administrador
   ativo. O fluxo não cria contas, não altera senhas, recusa execução com
   migration pendente e pode ser repetido sem efeito.
3. Entre com o login e a senha da conta Fiscal. Use **"Atuar como
   Administrador"** (no topo; no celular, no topo do menu) e **"Voltar a
   Fiscal"** (faixa azul). Ao sair e entrar de novo, a sessão começa como
   Fiscal.

Atenção: quem conhece a senha dessa conta Fiscal passa a ter os poderes do
Administrador. Toda troca é registrada na auditoria ("Perfil alternado para
Administrador" / "Perfil alternado para Fiscal") em nome da conta Fiscal.

## Limpar a demonstração

Não use o banco da VM e não importe dumps. Para reiniciar, descarte o banco demo
no provedor autorizado, crie outro banco/role contendo `demo`, reaplique as
migrations e recrie o administrador.

## Arquivos

Uploads de documentos e planilhas permanecem desabilitados. A Vercel limita o
corpo da função a 4,5 MB e não fornece o volume persistente usado pela VM.
