# Sprint 46 — Lupa do logotipo escaneando

## Solicitação

Animação no ícone do FiscalSema (lupa) com sensação de análise ativa: brilho
percorrendo a lente, varredura de um lado para o outro e pulsação
sincronizada; discreta e contínua; sem alterar desenho, tamanho, posição ou
identidade; sem mexer nas animações existentes; respeitar
`prefers-reduced-motion`.

## Verificação prévia

O `logo.svg` (Sprint 41) já tinha varredura (linha amarela), anel pulsando e
"check" se desenhando, todos em 3 s. A varredura andava só 9 px e quase não
aparecia no tamanho real (38 px). O padrão foi **reaproveitado**: mesmo ritmo,
mesmas cores (menta #44dc9c e amarelo #f5b301), mesmas formas.

## Incluído (somente no logotipo)

- Linha de varredura atravessa toda a lente, indo e voltando (3 s por passada).
- Feixe de brilho menta acompanha a linha dentro da lente.
- A lente acende levemente e o anel externo pulsa no meio de cada passada.
- Versão parada `logo-estatico.svg` (mesmo desenho), usada pelo `<picture>`
  quando o computador pede menos movimento e quando a pessoa escolhe "Sem".
