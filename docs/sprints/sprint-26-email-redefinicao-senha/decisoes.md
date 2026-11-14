# Decisões da Sprint 26

1. **SMTP do próprio Django**, sem dependência nova.
2. **Liga só com credenciais**: sem usuário e senha, o envio continua fictício
   (ambientes de teste e CI não enviam e-mail).
3. **Senha de app do Gmail** (exige verificação em duas etapas na conta
   Google); fica só na Vercel como variável secreta.
4. **Senha temporária por segredo do GitHub**, nunca por campo visível do
   fluxo; troca obrigatória no próximo acesso; máximo de 24 caracteres
   (regra de senha do sistema).
5. Lógica de e-mail extraída em função para poder ser testada fora do
   ambiente demo (a configuração demo recusa banco local).

## Riscos

- O envio depende de a Vercel permitir SMTP na porta 587 — confirmar no teste real.
- Limite diário de envio do Gmail (suficiente para a demonstração).
