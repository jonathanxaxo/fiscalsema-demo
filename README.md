# FiscalSema Demo

Este repositório é destinado exclusivamente a demonstração e testes.
Não contém e não deve receber dados reais do ambiente `fiscalsema-light`.

O projeto usa Django em uma Vercel Function e um PostgreSQL exclusivo da demo.
Docker, Nginx, banco, documentos, usuários e credenciais da VM não fazem parte
desta versão.

## Segurança essencial

- `DEBUG=False`;
- banco obrigatório por `DATABASE_URL`;
- bloqueio de hosts e nomes associados ao ambiente real;
- cookies seguros em HTTPS;
- CSRF, autenticação, autorização, rate limiting e auditoria preservados;
- cadastro público e uploads desabilitados;
- uma única conta administrativa inicial, criada por variáveis de ambiente.

Leia `docs/README.md` antes de qualquer publicação. As mudanças são registradas
por sprint, sem misturar o código executável com a documentação de evolução.
