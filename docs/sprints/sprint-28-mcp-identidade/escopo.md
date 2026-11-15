# Sprint 28 — MCP por identidade (OAuth)

## Decisão do responsável

Autorizado por clique ("Autorizo tudo"): instalar `django-oauth-toolkit==3.4.1`
e dependências fixadas, criar a migração OAuth e, se os testes passarem,
PR + merge + workflow `migrate-demo`.

## Incluído

- Servidor OAuth 2.1 próprio (django-oauth-toolkit) com:
  metadados RFC 8414 e RFC 9728 na raiz, `/oauth/authorize/`, `/oauth/token/`,
  `/oauth/revoke_token/` e registro dinâmico `/oauth/register/` (RFC 7591).
- Escopos: `fiscalsema.ler` (consultar) e `fiscalsema.propor` (propor
  rascunhos pendentes). Execução de alterações fica para a Sprint 30.
- PKCE S256 obrigatório, só redirecionamento https, cliente público, código
  válido por 2 minutos, token de acesso de 1 hora, renovação com rotação e
  proteção contra reuso, tokens guardados só como hash (RFC 9700).
- Registro dinâmico aberto com regras mínimas e limite global por hora
  (`MCP_DCR_PER_HOUR`, padrão 20). Registrar não dá acesso a nada.
- Tela de consentimento no visual do FiscalSema, sempre exibida.
- Endpoint `/mcp` (Streamable HTTP, sem estado, JSON-RPC 2.0):
  `initialize`, `ping`, `tools/list`, `tools/call`; 401 com
  `WWW-Authenticate ... resource_metadata=...`.
- 7 ferramentas de consulta (mesmos serviços de visibilidade da web) e
  `propor_rascunho` (só com `fiscalsema.propor`, cria rascunho PENDENTE).
- Conta inativa/bloqueada perde o acesso na hora; limite por minuto
  (`MCP_PER_MINUTE`, padrão 30); auditoria de cada chamada, autorização e
  revogação em `ApiAccessEvent` (sem guardar o conteúdo devolvido).
- Minha conta → Conexões externas: lista clientes de IA conectados, mostra o
  endereço do conector e permite **Revogar**.

## Fora do escopo

- Ferramentas de análise e divergências (Sprint 29).
- Alterações autorizadas com confirmação (Sprint 30).
- Homologação, atesto, liquidação e pagamento: nunca por IA.
- Clientes com redirecionamento `http://localhost` (ex.: Claude Code local)
  ficam bloqueados nesta etapa por segurança.
