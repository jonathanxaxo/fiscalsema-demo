# Sprint 45 — Sistema vivo mesmo com "reduzir movimento" e mais efeitos

## Solicitação

"No sistema atualmente está parado e não está pulsando nem funcionando os
efeitos"; "ícones, dashboard e tudo que der para ficar vivo e pulsante, as
barras e outras coisas legais"; "deixar funcionando no Vercel" e mostrar no
vídeo.

## Diagnóstico

O CSS e o JS das Sprints 41–44 estavam publicados. Quando o computador pede
"reduzir movimento" (ex.: Windows › Acessibilidade › Efeitos visuais ›
Efeitos de animação desligado), o sistema desligava **todo** movimento —
pulsos, barras, contagem e ondulação —, e a tela ficava parada.

## Correção

- Sem escolha da pessoa, o pedido do sistema operacional vira **Calmo**
  (continua pulsando, mais devagar) em vez de parar tudo.
- **Vivo** e **Sem** escolhidos no menu sempre valem; "Sem" continua
  desligando todo movimento.
- O bloqueio total por `prefers-reduced-motion` só vale se o JavaScript não
  rodar.

## Mais vida

Ícones do menu respiram em sequência, sino balança quando há pendências,
logotipo brilha, barras do gráfico mensal pulsam em sequência, botões
principais com reflexo e avatar com anel vivo.

## Fora do escopo

Nenhuma regra, modelo, migração, dependência, workflow ou variável muda.
