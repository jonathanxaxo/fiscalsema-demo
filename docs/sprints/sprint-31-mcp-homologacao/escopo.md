# Sprint 31 — MCP: testes de segurança, compatibilidade, homologação e guia

## Decisão do responsável

"continuar" após o plano apresentado (Sprint 31: testes de segurança,
compatibilidade por cliente, homologação e guia). Sem dependência, sem
migração e sem variável nova.

## Incluído

- `api_v1/test_mcp_seguranca.py` (20 testes) simulando ataques: verificador
  PKCE errado, código reutilizado ou usado por outro cliente, redirecionamento
  não cadastrado, escopo desconhecido, aumento de escopo na renovação, token de
  outro recurso, token na URL, revogação pelo endpoint oficial, gestão do
  registro sem token e com redirecionamento http, CSRF e bloqueio de iframe
  no consentimento; compatibilidade (versões de protocolo, lote JSON,
  envelopes inválidos, ping/OPTIONS/no-store, corpo grande, erros sem
  detalhes internos) e catálogo de ferramentas (nada genérico ou proibido,
  cada escopo vê exatamente as suas ferramentas).
- `docs/mcp/guia-conexao.md`: como conectar cada cliente, escopos, problemas comuns.
- `docs/mcp/roteiro-homologacao.md`: 20 verificações manuais.
- Base de conhecimento do Assistente Arise: seção "Conectar uma IA externa".

## Resultado

Nenhuma falha de segurança encontrada: todos os ataques simulados foram
recusados pelo código das Sprints 28–30 sem ajuste.

## Fora do escopo

- Homologação manual em produção: feita pelo responsável com o roteiro.
- Callback `http://localhost` (Claude Code local): segue bloqueado.
