# Decisões — Sprint 29

1. **Análise usa o escopo de leitura** (`*_visible_to`), não o de escrita:
   quem só consulta também pode conferir um documento. Por isso a análise
   ficou em `api_v1/analise.py`, separada do fluxo de rascunhos (que exige
   permissão de escrita).
2. **Classificação simples e objetiva** (igual/diferente/ausente/vazio) feita
   pelo sistema; a interpretação continua com a pessoa.
3. **Valores do documento não vão para a auditoria**: só ferramenta,
   contrato, quantidade de campos e cliente.
4. **Documentos sem download pelo MCP**: evita vazamento de arquivo e o link
   antigo da API técnica (`content_url`) é removido da resposta.
5. Nenhuma ferramenta nova grava dados; todas têm `readOnlyHint`.
