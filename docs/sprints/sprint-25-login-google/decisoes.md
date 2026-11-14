# Decisões da Sprint 25

1. **OIDC próprio** (decisão do responsável na Sprint 24): sem biblioteca nova;
   o `id_token` vem direto do endpoint de token do Google por TLS verificado,
   o que a especificação OIDC aceita no lugar da checagem de assinatura.
2. **Prova de posse por senha** para vincular a um cadastro existente; conta
   sem senha utilizável depende do Administrador definir uma senha temporária.
3. **Nada do cadastro é alterado** pelo login ou vínculo; o nome vindo do
   Google é ignorado.
4. **Sem cadastro automático** nesta sprint; e-mail desconhecido é recusado.
5. **Não perder o acesso**: não é possível desvincular o único método de acesso.
6. **Mensagens na tela de login**: o layout de login não mostrava mensagens do
   sistema; foram incluídas para o usuário entender por que o acesso foi negado.

## Pendências

- Criar o cliente OAuth no Google Cloud (responsável) e cadastrar as variáveis na Vercel.
- Confirmar se o domínio institucional usa Google Workspace (para exigir `hd`).
