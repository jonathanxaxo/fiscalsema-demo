# Decisões — Sprint 52

- **Decidir na reabertura, não no fechamento.** O aviso de "fechando a aba"
  também dispara ao atualizar ou trocar de tela; por isso o sistema confere
  quando a aba é aberta.
- **Perguntar às outras abas** evita pedir senha ao abrir um registro em nova
  aba com o sistema ainda aberto.
- **Quem encerra é o servidor**, com proteção CSRF e registro na auditoria.
- **Na dúvida, não derruba:** sem `sessionStorage` ou `BroadcastChannel`, segue
  normalmente; as regras de 1 hora e de fechar o navegador continuam protegendo.
