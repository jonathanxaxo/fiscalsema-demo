---
titulo: NF pelo valor dimensionado, devolução e NF corrigida
rotas: contracts:invoice_detail contracts:invoice_create contracts:invoice_update contracts:invoice_return
perfis: FISCAL USUARIO_CONSULTA
palavras: dimensionado dimensionada devolver devolucao devolvida corrigida corrigir substitui substituir valor diferente servicos cobrados faturar faturada
---
**Serviços cobrados na NF**: ao cadastrar a NF de uma OS com catálogo, marque "Serviços cobrados nesta NF" (só aparecem serviços **homologados** e ainda não cobrados em outra NF).
**Valor dimensionado** = soma das UST/HST/USN dos serviços × valor unitário da OS. A tela da NF mostra "Valor da NF × valor dimensionado" e a diferença. A NF deve ter exatamente o valor dimensionado.
**Devolver para correção**: na NF, botão "Devolver para correção" (data e motivo obrigatórios). NF com pagamento não pode ser devolvida. A NF devolvida **sai de todos os cálculos** (saldo, painel, relatórios, prestação de contas), não recebe pagamento e fica no histórico.
**NF corrigida**: cadastre a nova NF e escolha em "Substitui a NF devolvida" qual ela corrige (uma única substituição); ela pode cobrar os mesmos serviços.
Avisos no sino: NF com valor diferente do dimensionado, NF devolvida aguardando a corrigida, serviço aceito sem Termo e serviço homologado sem NF.
