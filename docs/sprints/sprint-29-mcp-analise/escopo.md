# Sprint 29 — MCP: consultas novas e análise de divergências

## Decisão do responsável

Plano aprovado por clique ("Autorizo tudo"): implementar, testar e, se tudo
passar, PR + merge. Sem dependência nova, sem migração, sem variável nova.

## Incluído (todas as ferramentas usam o escopo `fiscalsema.ler`)

- `consultar_rateios`, `consultar_execucoes`.
- `consultar_pagamentos` (sempre com o aviso: não é atesto nem autorização de pagamento).
- `consultar_posicao_financeira`.
- `listar_documentos`: nome, tipo, versão, data e hash; **sem** baixar o arquivo.
- `conferir_nota_fiscal`: conferência automática informativa de uma NF.
- `analisar_divergencias`: a IA envia os valores que leu no documento e o
  sistema compara com o registro gravado, campo a campo:
  `IGUAL`, `DIFERENTE`, `AUSENTE_NO_DOCUMENTO`, `VAZIO_NO_SISTEMA`, marcando
  campos críticos. Aceita formatos brasileiros (R$ 1.234,50; 31/12/2026).
  **Não grava nada e não cria rascunho.**
- `consultar_meus_rascunhos`: situação dos rascunhos da própria pessoa.

## Fora do escopo

- Executar alterações (Sprint 30, com código de confirmação).
- Ler o conteúdo de arquivos pelo MCP.
- Homologação, atesto, liquidação e pagamento: nunca por IA.
