# Decisões — Sprint 46

- **Animação dentro do SVG.** Assim nenhuma regra de CSS compartilhada muda e
  as outras animações ficam intactas.
- **`<picture>` com versão parada.** A preferência "reduzir movimento" nem
  sempre chega dentro de um SVG carregado como imagem; o `<picture>` troca o
  arquivo pelo próprio navegador. `display: contents` mantém o layout igual.
- **Modo "Sem" também para o logotipo**, que antes continuava animado nesse modo.
