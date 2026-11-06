# Decisões da Sprint 07

1. Descrições das listas usam somente informações já exibidas nas colunas;
   nenhuma regra nova foi descrita.
2. Cores de status de OS: "Em execução" e "Concluída" em verde; "Suspensa" em
   amarelo; "Cancelada" em vermelho; demais estados em cinza (neutro).
   Ajustável se o usuário preferir outra leitura.
3. Na lista de rascunhos, "Pendente" aparece em amarelo (requer revisão).
4. O menu móvel usa a variável CSS `--menu-top`, atualizada por JavaScript com
   a posição real do cabeçalho. Sem JavaScript, mantém o valor anterior (64 px).
5. Nos rascunhos, as informações de lote, origem, autoridade e confiança
   passaram de parágrafos para lista de definição (`dl`), com os mesmos rótulos.
6. Formulários com layout próprio (encerramento, transferência, pagamento,
   nota fiscal etc.) não foram alterados nesta sprint.
