# Decisões da Sprint 05

1. **Casas decimais (M6):** o usuário aprovou o exemplo de 2 casas. Para não
   esconder informação, foi adotado "no mínimo 2, no máximo 4": `20.0000` →
   `20,00`; `12.3456` → `12,3456`. O banco continua com 4 casas.
2. Os campos de cota anual (`floatformat:"-7"`) e os quantitativos do painel
   (`floatformat:"-4"`) não foram alterados, por já não exibirem zeros
   desnecessários.
3. **CNPJ/CPF (M7):** máscara aplicada somente na exibição; valores com
   quantidade de dígitos diferente de 11 ou 14 são mostrados como estão.
4. **Rolagem (A3):** aviso em texto, criado por JavaScript somente quando a
   tabela é maior que a tela; sem bibliotecas.
5. Um teste existente foi atualizado (não removido) porque verificava o
   formato antigo de exibição, alterado por decisão do usuário.
6. Numeração: esta sprint recebeu o número 05 por ser a quinta executada.
