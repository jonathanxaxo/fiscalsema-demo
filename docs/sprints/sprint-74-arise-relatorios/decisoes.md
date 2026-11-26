# Decisões — Sprint 74

1. **Sugestões por contexto.** `suggestions_for(profile, contract=...)` só
   troca as sugestões quando há contrato validado no backend. O chat
   flutuante recebe as duas listas e escolhe pelo contrato ativo exibido.
2. **Auxiliar sem valores.** As perguntas dela tratam de OS e prazos,
   coerentes com o painel sem valores da Sprint 60.
3. **Relatórios.** A regra de impressão fica no `app.css`, escopada a
   `.report-page`, valendo para os dois relatórios. As tabelas largas saem
   inteiras (letra 8 pt, quebra de linha nas células, cabeçalho repetido) e
   a dica de rolagem da tela não é impressa. O relatório gerencial caiu de 5
   para 2 páginas e o do contrato de 5 para 3, sem perder conteúdo.
4. **Frase de dados fictícios.** Removida do relatório gerencial, seguindo a
   decisão da Sprint 72. O aviso legal permanece por proteger contra uso
   indevido do relatório.
5. **Usabilidade comprovada.** A varredura automática não encontrou links
   quebrados nem rolagem horizontal em 14 telas (1440 e 390 px). O texto
   cortado nos indicadores do celular já havia sido corrigido na Sprint 73.
