# Guia — conectar um cliente de IA ao FiscalSema Demo (MCP)

Endereço do conector: `https://fiscalsema-demo.vercel.app/mcp`
(transporte Streamable HTTP, autenticação OAuth 2.1 com PKCE e registro dinâmico).

## Clientes

| Cliente | Situação | Como conectar |
|---|---|---|
| Claude (claude.ai, navegador) | Suportado | Configurações → Conectores → Adicionar conector personalizado → URL acima → Conectar |
| Claude Desktop | Suportado | Mesmo caminho (os conectores da conta aparecem no Desktop) |
| Claude no celular | Usa os conectores já adicionados na conta | Adicione pelo navegador primeiro |
| MCP Inspector (testes) | Suportado se o callback for https | Use a URL acima e o fluxo OAuth do Inspector |
| Claude Code local / clientes com callback `http://localhost` | **Não suportado nesta versão** | Redirecionamento só em https (decisão de segurança da Sprint 28) |
| Outros clientes MCP com OAuth (ex.: ChatGPT conectores) | Esperado funcionar se seguirem o padrão MCP de autorização | Mesma URL; não homologado nesta sprint |

## Permissões (escopos)

| Escopo | Libera |
|---|---|
| `fiscalsema.ler` | 15 ferramentas de consulta e análise (somente leitura) |
| `fiscalsema.propor` | `propor_rascunho` (rascunho pendente, válido por 24 h) |
| `fiscalsema.executar` | `executar_proposta` — só com o código de uso único gerado na tela; pagamento nunca |

Escopo novo exige reconectar (o token antigo mantém os escopos de quando foi autorizado).

## Problemas comuns

- **"A conta não está ativa"**: a conta está pendente, bloqueada ou inativa.
- **"Esta conexão não tem permissão…"**: reconecte marcando o escopo indicado.
- **Entrou com Google e caiu na tela inicial**: clique em Conectar de novo no cliente (você já estará logado).
- **"Limite de chamadas por minuto"**: aguarde 1 minuto (padrão 30 chamadas/min).
- **Código recusado**: vale 10 minutos, uma vez, até 5 tentativas; gere outro em Rascunhos da IA.

## Revogar

Minha conta → Conexões externas → **Revogar** (apaga os tokens e impede a renovação).
