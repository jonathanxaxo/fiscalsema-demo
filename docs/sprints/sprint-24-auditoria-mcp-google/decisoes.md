# Decisões, arquitetura e plano (Sprint 24)

## Arquitetura do MCP remoto

```text
Cliente de IA (Claude, ChatGPT, ...)
  │ OAuth 2.1 (código + PKCE) → login no FiscalSema → "Autorizar conexão" (escopos)
  ▼
FiscalSema (Vercel)
  ├─ /.well-known/oauth-protected-resource e oauth-authorization-server
  ├─ /oauth/authorize, /oauth/token, /oauth/revoke   (django-oauth-toolkit)
  ├─ /mcp  (Streamable HTTP, sem estado, JSON) → ferramentas → serviços oficiais
  ├─ /mcp/confirmar/<proposta>  (confirmação autenticada quando o cliente não confirma sozinho)
  └─ PostgreSQL: conexões, tokens em hash, propostas, auditoria
```

- Escopos: `fiscalsema.ler`, `fiscalsema.propor`, `fiscalsema.executar`.
- Em cada chamada: token, revogação, conta ativa, perfil atual, contrato em
  `contracts_visible_to` / `contracts_writable_by`, escopo e limite.
- A identidade é a do FiscalSema autorizada na conexão (nunca a conta do
  cliente de IA); token preso à conta que autorizou (a troca de perfil na
  tela não altera o que a IA pode fazer).
- Sem SQL, sem edição genérica, sem buscar URLs vindas da IA (anti-SSRF).
- Homologação, atesto, liquidação e autorização de pagamento: fora da IA.

## Fluxo de alteração autorizada

1. Consultas → comparação feita pela IA com o documento que ela leu.
2. `propor_correcao` (dados estruturados + evidência) → proposta pendente com
   identificador, `baseline_hash`, validade (30 min) e chave de idempotência.
3. "Sim" no chat **não executa**. Confirmação: recurso nativo do cliente
   (quando houver) **e** código de uso único; ou link "Confirmar no
   FiscalSema" com a pessoa logada vendo antes/depois.
4. `executar_proposta(id, código)`: revalida dono, escopo, permissão atual,
   validade, código, hash do estado e idempotência; grava pelos serviços
   oficiais; audita; devolve o resultado.

## Login Google (OpenID Connect próprio, sem dependência)

- Fluxo código + PKCE + `state` + `nonce`; token trocado diretamente com o
  Google por TLS (permite dispensar a checagem da assinatura, conforme a
  especificação OIDC); validar `iss`, `aud`, `exp`, `nonce`, `sub`,
  `email_verified` e `hd` (se o domínio usar Workspace).
- Nova tabela `ExternalIdentity` (usuário, provedor, `sub` único, e-mail, data).
- Conta existente com o mesmo e-mail: vínculo **só com prova de posse**
  (senha atual do FiscalSema, autenticação recente) ou aprovação do
  Administrador; nada além do vínculo é alterado.
- Sem cadastro: e-mail autorizado → usuário **pendente de aprovação**, sem
  perfil Fiscal automático, em transação única; solicitação ao Administrador.
- Política de novos cadastros por variáveis de ambiente:
  `ALLOWED_SIGNUP_DOMAINS` (domínio institucional) e `ALLOWED_SIGNUP_EMAILS`
  (exceção individual do professor, endereço exato; o domínio dele não é
  liberado). Contas existentes não são afetadas pela política.
- Cadastro com senha: **desligado na demo** até haver envio real de e-mail.
- "Minha Conta": métodos de acesso, contas Google, conexões externas,
  revogação; impedir que o usuário fique sem nenhum método de acesso.

## Dependências e custos

| Item | Decisão | Custo |
|---|---|---|
| Login Google | OIDC próprio (biblioteca padrão) | Cliente OAuth do Google: gratuito |
| Servidor OAuth do MCP | `django-oauth-toolkit` 3.4.1 (+ `requests`, `urllib3`, `oauthlib`, `jwcrypto`/`cryptography`) — instalar só na Sprint 27 com autorização | Gratuito |
| E-mail real | Adiado | — |

## Riscos principais

Tomada de conta por e-mail igual; token vazado; "sim" falso ou prompt
injection; execução duplicada/concorrente; vazamento entre usuários;
redirecionamento malicioso no OAuth; SSRF; mistura de ambientes;
compatibilidade variável dos clientes de IA com MCP remoto e OAuth. As
mitigações estão no plano apresentado ao responsável e serão testadas.

## Plano das próximas sprints (cada uma com autorização)

| Sprint | Entrega |
|---|---|
| 25 | Login Google, `ExternalIdentity`, vínculo com prova de posse, "Minha Conta → métodos de acesso" |
| 26 | Política de e-mails, cadastro automático pendente, exceção do professor |
| 27 | Servidor OAuth (django-oauth-toolkit), `/mcp` remoto, escopos, conexões e revogação |
| 28 | Novas ferramentas de consulta e `propor_correcao` com evidências |
| 29 | Validade, idempotência, código de confirmação, página de confirmação, `executar_proposta` |
| 30 | Testes de segurança, compatibilidade por cliente, homologação e guia de publicação |

## Pendências do responsável

- Verificar os registros MX do domínio institucional (Google Workspace ou não).
- Criar, quando chegar a Sprint 25, o cliente OAuth no Google Cloud
  (gratuito) e cadastrar `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` na Vercel.
