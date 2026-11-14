# Segurança do FiscalSema Demo

| Controle | Original | Demo | Situação | Justificativa |
|---|---|---|---|---|
| Política de senha | Validadores Django e regras próprias | Mesmos validadores | Igual | Código preservado |
| Autenticação e autorização | Backend e escopos por contrato | Mesma implementação | Igual | Dados separados |
| CSRF | Middleware e origens confiáveis | HTTPS e origens por ambiente | Adaptado | Domínio Vercel |
| Cookies | HttpOnly e SameSite | HttpOnly, SameSite e Secure | Mais restritivo | HTTPS |
| DEBUG | Desativado | Desativado | Igual | Falha fechada |
| X-Frame-Options | Django e Nginx | Django e Vercel | Adaptado | Sem Nginx |
| Headers | Django e Nginx | Django e `vercel.json` | Adaptado | Sem Nginx |
| Rate limiting | PostgreSQL | PostgreSQL demo | Igual | Estado compartilhado |
| Bloqueio de login | PostgreSQL | PostgreSQL demo | Igual | Estado compartilhado |
| Permissões | Backend | Backend | Igual | Código preservado |
| Validação de upload | Extensão, conteúdo e regras de domínio | Uploads desabilitados | Mais restritivo | Sem volume persistente nesta versão |
| Limite de arquivo | Limites por tipo no backend | 4 MB e recurso desabilitado | Mais restritivo | Compatível com o limite da função e sem persistência local |
| Logs sem credenciais | Filtros e arquivos restritos | Somente console, sem segredos | Adaptado | Logs efêmeros da função |
| Auditoria | PostgreSQL | PostgreSQL demo | Igual | Código preservado |
| Segredos | Arquivo externo à aplicação | Secrets da Vercel | Adaptado | Nada no Git |
| Variáveis de ambiente | Arquivo protegido na VM | Painel seguro da Vercel | Adaptado | `.env` real ignorado; exemplo sem valores |
| Credenciais hardcoded | Proibidas | Proibidas e verificadas por scanner | Igual | Falha no CI quando detectado padrão conhecido |
| `.gitignore` e `.dockerignore` | Protegem artefatos operacionais | Reforçados para demo | Adaptado | Excluem bancos, dumps, documentos, mídias, logs e chaves |
| Banco | PostgreSQL da VM | PostgreSQL demo exclusivo | Adaptado | Isolamento absoluto |
| Privilégio do banco | Usuário próprio da aplicação | Usuário exclusivo e mínimo da demo | Igual | Sem conta administrativa na aplicação |
| Assistente IA (Sprint 21) | Não existe | Chat somente de ajuda, chave só no backend, limite por minuto/dia, conversas isoladas por usuário (30 dias), auditoria só de metadados | Novo na demo | Blocos do prompt tratados como dados; sem acesso da IA ao banco |
| Login com Google (Sprint 25) | Não existe | OpenID Connect com PKCE, state e nonce; vínculo a cadastro existente só com prova de posse; segredo do cliente só na Vercel | Novo na demo | Não altera perfil, organização nem permissões |
| E-mail (Sprint 26) | SMTP institucional | SMTP (Gmail, senha de app) só com variáveis na Vercel; fictício sem elas | Adaptado | Senha do e-mail só como segredo; senha temporária por segredo do GitHub com troca obrigatória |

Nenhum dado, credencial, documento, usuário ou histórico do banco real pode ser
copiado para este projeto.
