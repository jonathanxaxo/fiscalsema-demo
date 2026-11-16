# Sprint 53 — Lupa no modo Calmo

## Solicitação

Corrigir somente o logotipo do FiscalSema Demo: a lupa parou de escanear nas
telas de entrada e do sistema, embora as demais animações continuem ativas.

## Causa confirmada

Quando o computador pede redução de movimento, o sistema escolhe o modo
`Calmo`, que mantém os efeitos mais lentos. O `logo.svg` ainda possuía uma
regra própria que desligava toda a animação, contrariando esse padrão.

## Limite

- manter desenho, cores, tamanho e posição do logotipo;
- manter as demais animações e funcionalidades sem alteração;
- manter a versão estática apenas para a escolha explícita `Sem`.
