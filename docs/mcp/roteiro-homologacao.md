# Roteiro de homologação manual do MCP (Sprint 31)

Executar com uma conta de demonstração, só com dados fictícios. Marcar cada
item com OK/FALHOU e anotar data, cliente e observação.

## A. Conexão
1. [ ] Adicionar o conector no Claude com a URL do guia.
2. [ ] O Claude abre a tela de login do FiscalSema (não pede senha no chat).
3. [ ] A tela "Autorizar" mostra o nome do cliente, a conta logada e os escopos.
4. [ ] Cancelar não conecta; Autorizar conecta.
5. [ ] Minha conta → Conexões externas mostra o cliente.

## B. Consultas (escopo ler)
6. [ ] "Liste meus contratos autorizados" mostra só os contratos da conta.
7. [ ] Resumo, itens, empenhos, OS, NF, rateios, execuções, pagamentos e posição financeira respondem.
8. [ ] Pagamentos e NF vêm com o aviso "não constitui atesto…".
9. [ ] "Analisar divergências" aponta IGUAL/DIFERENTE e diz que nada foi gravado.
10. [ ] Com outra conta (sem o contrato), a IA recebe "sem permissão".

## C. Proposta e execução
11. [ ] A IA propõe uma alteração de observações; nada muda no contrato.
12. [ ] O rascunho aparece em Rascunhos da IA com antes/depois e validade de 24 h.
13. [ ] Responder "sim" no chat não executa.
14. [ ] Gerar código, digitar no chat → execução gravada; o contrato mostra a alteração.
15. [ ] Repetir o mesmo código → "já executada", sem gravar de novo.
16. [ ] Código errado 5 vezes → código anulado.
17. [ ] Proposta de pagamento não oferece código.

## D. Revogação e auditoria
18. [ ] Revogar em Minha conta → a próxima chamada da IA falha.
19. [ ] Auditoria (API/eventos) mostra as chamadas com ferramenta e cliente, sem conteúdo de documentos nem código.
20. [ ] Bloquear a conta de teste → a IA perde o acesso na hora.

## Evidência automatizada

`api_v1/test_mcp_remoto.py` (36) e `api_v1/test_mcp_seguranca.py` (20)
cobrem os mesmos pontos sem internet.
