# Decisões — Sprint 42

- **Só CSS e JS de apresentação.** O chat ficou mais limpo sem mexer nos
  templates nem no fluxo; assim nada do funcionamento validado nas Sprints
  21–34 muda.
- **Avatar do Arise por CSS.** A bolinha viva é um `::before` no rótulo da
  mensagem do assistente: não exige mudar o HTML gerado pelo JS.
- **Aviso em 10 segundos nas duas telas.** O aviso continua aparecendo a
  cada abertura do painel flutuante e a cada carregamento da tela cheia, e
  depois some com transição suave. O texto do aviso não muda.
- **Camada genérica para as telas restantes.** Em vez de alterar dezenas de
  templates, a animação vale para os blocos diretos de `.content`, para os
  formulários simples, listas de detalhes e o cartão de login.
- **Acessibilidade preservada.** Os modos "Calmo" e "Sem" e o
  `prefers-reduced-motion` continuam desligando ou suavizando os movimentos.
