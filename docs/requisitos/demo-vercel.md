# Requisitos da demo Vercel

1. Não acessar ou alterar o banco da VM.
2. Não copiar dados, usuários, documentos ou credenciais reais.
3. Usar `APP_ENVIRONMENT=demo` e `DATABASE_URL` exclusiva.
4. Manter `DEBUG=False`, autenticação, autorização, CSRF, rate limiting,
   bloqueio de login e auditoria.
5. Iniciar com banco vazio e somente uma conta administrativa.
6. Manter cadastro público e uploads desabilitados.
7. Exibir permanentemente que o ambiente usa dados fictícios.
8. Não executar push ou deploy sem autorização específica.
