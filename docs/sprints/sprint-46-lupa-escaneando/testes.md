# Testes — Sprint 46

Novos: `core/test_logo_escaneando.py` (3 testes).

## Verificação no navegador (Playwright)

| Situação | Arquivo usado | Quadros diferentes em 2,8 s |
|---|---|---|
| Normal | logo.svg | 4 (animando) |
| Clicou "Sem" | logo-estatico.svg | 1 (parado) |
| Voltou "Vivo" | logo.svg | 4 |
| Computador pede menos movimento | logo-estatico.svg | 1 (parado; brilho CSS `none`) |

Posição e tamanho do logotipo no cabeçalho: 38 × 38 px, no mesmo lugar.

As outras animações continuam iguais: ícone flutuante `fs-fab`, ponto do título
`fs-dot`, números `fs-beat`, barras `fs-glow-bar`, ícones do menu `fs-bob` e
`fs-beat`, sino `fs-swing`, brilho do logo `fs-logo-glow`.

| Suíte completa | **685 testes OK** |
|---|---|
| Scanner / MCP / migrações | PASS / OK / sem mudanças |
