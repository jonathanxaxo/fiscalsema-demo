# Decisões da Sprint 23

1. **Nome "Assistente Arise"** a pedido do responsável (substitui a decisão
   da Sprint 21 de não exibir o nome).
2. **Um único script** para a página e o painel, evitando duas lógicas de chat.
3. **Continuidade**: o painel guarda só o número da conversa na aba
   (`sessionStorage`); as mensagens vêm do servidor e só do próprio usuário.
4. **Painel oculto** na tela cheia do assistente (evita dois chats na mesma
   página), no login e na impressão.
5. **Acessibilidade**: botão com `aria-expanded`, painel `role="dialog"`,
   fechar com Esc devolvendo o foco ao ícone, respostas em `aria-live`.
