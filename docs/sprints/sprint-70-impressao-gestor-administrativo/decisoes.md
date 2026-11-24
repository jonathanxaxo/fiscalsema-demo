# Decisões — Sprint 70

1. A falha não estava nos dados: a prévia era aberta enquanto o corpo da
   nova aba ainda estava invisível durante a verificação de sessão.
2. A correção foi limitada ao script de impressão automática compartilhado,
   portanto atende todo perfil que já possua acesso a um relatório, sem alterar
   painéis, permissões ou cálculos.
3. Quando a página já está liberada, o comportamento anterior é preservado.
4. Quando a classe `fs-verificando` está presente, um observador aguarda sua
   remoção e a próxima pintura do navegador antes de chamar `window.print()`.
5. A Sprint não amplia acesso: cada perfil continua recebendo somente os dados
   autorizados pelas regras atuais.
