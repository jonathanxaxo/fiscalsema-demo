# Decisões — Sprint 30

1. **Código gerado na tela, não no chat**: só quem está logado no FiscalSema
   vê o código, junto com o antes/depois. Isso impede que um "sim" falso ou
   um texto malicioso (prompt injection) execute algo.
2. **8 caracteres sem letras ambíguas** (formato `XXXX-XXXX`), 10 minutos,
   5 tentativas e HMAC com a chave do sistema: adivinhar é inviável.
3. **Mesmo cliente de IA**: a proposta só é executada pela conexão que a criou.
4. **Reuso de `confirm_assistant_draft`**: a execução pelo chat passa pelas
   mesmas validações da tela; o evento registra `canal: mcp_codigo`.
5. **Pagamento bloqueado** na execução pela IA, mesmo com escopo.
6. **Validade de 24 h** só para propostas do MCP; a API técnica antiga não muda.
7. Regra de negócio existente preservada: campos estruturais de contrato em
   andamento continuam bloqueados também pela via do código.
