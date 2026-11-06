# Decisões da Sprint 12

1. **Valores proporcionais:** o valor e a vigência do contrato real não são
   conhecidos; o comando usa no máximo 50% do saldo disponível e distribui
   entre os itens (45%, 35% e 20%) e empenhos (40% e 30%).
2. **Datas relativas:** a partir de hoje, limitadas à vigência do contrato.
3. **Situações das OS:** concluída e paga; em execução com NF pendente de
   pagamento; em execução vencida e sem rateio (gera alertas); assinada;
   rascunho.
4. **Identificação:** prefixo `DEMO-` nos números e marcação
   `[DEMO-APRESENTACAO]` em observações/descrições.
5. **Idempotência:** se o item `DEMO-1` já existir, nada é criado.
6. **Segurança:** o contrato precisa pertencer ao Fiscal informado; somente
   no ambiente demo; confirmação `CRIAR DADOS`; `migrate --check` antes.
7. **Irreversível:** sem exclusão física; remoção apenas recriando o banco.
