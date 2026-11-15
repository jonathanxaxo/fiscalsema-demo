# Decisões — Sprint 51

- **Recurso nativo do Django** (cookie de sessão sem validade), sem código novo.
- **Não deslogar ao fechar a aba.** Detectar o fechamento de aba no navegador
  não é confiável e também dispararia ao atualizar a página ou trocar de tela;
  o botão Sair e a regra de 1 hora cobrem esse caso.
- **As duas regras se somam:** fechou o navegador → sai; esqueceu aberto → sai
  após 1 hora sem uso.
