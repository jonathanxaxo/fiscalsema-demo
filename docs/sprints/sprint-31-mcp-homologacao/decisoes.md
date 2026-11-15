# Decisões — Sprint 31

1. **Testar como atacante**, não só o caminho feliz: cada teste tenta quebrar
   uma proteção (PKCE, uso único do código, vínculo ao cliente e ao recurso,
   escopo, CSRF, iframe).
2. **Homologação manual separada da automática**: o roteiro cobre o que só o
   cliente real (Claude) mostra, como as telas e a experiência no chat.
3. **Clientes com callback http continuam bloqueados**: preferimos segurança a
   compatibilidade; reavaliar se houver necessidade real.
4. **Arise explica a conexão**: a ajuda fica versionada na base de
   conhecimento, sem dar ao Arise acesso aos dados.
