# Sprint 25 — Login com Google e Minha conta

Primeira sprint de implementação do plano da Sprint 24.

## Incluído

- Botão **Continuar com Google** no login (aparece só com o cliente OAuth configurado).
- OpenID Connect próprio, sem dependência: código + PKCE (S256), `state`, `nonce`;
  token trocado diretamente com o Google por TLS; validação de emissor,
  audiência, `azp`, expiração, `iat`, `nonce`, `sub` e `email_verified`.
- Tabela `ExternalIdentity` (provedor + `sub` únicos) — migração `accounts/0009`.
- Fluxos:
  - identidade já vinculada → entra no **mesmo** usuário, respeitando a situação da conta;
  - mesmo e-mail sem vínculo → vínculo **só com prova de posse** (senha atual,
    com o mesmo limite de tentativas do login);
  - sem cadastro → recusado com mensagem (cadastro institucional é a Sprint 26).
- **Minha conta** (no topo, no lugar de "Alterar senha"): métodos de acesso,
  vincular e desvincular Google (com senha), conexões externas (lista).
- Auditoria: login Google, recusa, vínculo e desvínculo.

## Fora do escopo

Cadastro novo pelo Google e política de e-mails (Sprint 26); MCP remoto e
revogação de conexões (Sprint 27); validação do domínio `hd` (depende de
confirmar o Google Workspace da SEMA).
