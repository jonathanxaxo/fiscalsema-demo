# Decisões — Sprint 28

1. **django-oauth-toolkit em vez de OAuth feito à mão**: biblioteca madura,
   com PKCE, RFC 8414/9728/7591/8707 e armazenamento de token por hash.
   Escrever um servidor OAuth próprio seria mais arriscado.
2. **Registro dinâmico aberto**: o Claude (e outros clientes MCP) se
   registram sozinhos. Isso é seguro porque o registro não dá acesso; o
   acesso só nasce no consentimento da pessoa logada. Há teto por hora e só
   https/PKCE/authorization_code.
3. **Sem estado e sem SSE**: a Vercel Function não mantém conexão; o MCP
   aceita só POST com resposta JSON.
4. **Tool error em vez de HTTP 403** para escopo insuficiente: a IA recebe
   mensagem clara pedindo reconexão com o escopo certo.
5. **Rascunho ligado ao cliente OAuth** (`created_by_application`, SET_NULL);
   a credencial técnica antiga ficou opcional. Exatamente uma das duas origens.
6. **Login Google durante a conexão**: o retorno do Google vai para o início;
   basta clicar em conectar de novo no cliente (sessão já aberta).
