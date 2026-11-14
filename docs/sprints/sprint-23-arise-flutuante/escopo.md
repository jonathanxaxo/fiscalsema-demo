# Sprint 23 — Assistente Arise flutuante e metodologia da IA

## Solicitação

1. Registrar na Metodologia como o assistente foi feito (skills, práticas,
   tecnologias e lições).
2. Renomear para **Assistente Arise**.
3. Ícone flutuante de conversa que abre o chat num painel, em qualquer tela.

## Decisões do responsável (por clique)

- manter o item **Assistente Arise** no menu (tela cheia com histórico) **e**
  o ícone flutuante (painel rápido);
- PR + merge autorizados se os testes passarem.

## Incluído

- nome "Assistente Arise" em menu, telas, mensagens, prompt, auditoria e
  base de conhecimento;
- ícone redondo no canto inferior direito de todas as telas com login
  (exceto a própria tela cheia); painel com streaming, sugestões, nova
  conversa, "abrir em tela cheia" e fechar (X ou Esc); no celular ocupa a tela;
- o painel continua a última conversa da aba (buscando as mensagens do
  próprio usuário em `/assistente/conversas/<id>/mensagens/`);
- seção "Como o Assistente Arise foi construído" na Metodologia.

Sem migração, dependência ou variável nova.
