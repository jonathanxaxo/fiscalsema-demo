# FiscalSema Demo

Este repositório é destinado exclusivamente a demonstração e testes.
Não contém e não deve receber dados reais do ambiente principal.

O projeto usa Django em uma Vercel Function e um PostgreSQL exclusivo da demo.
Docker, Nginx, banco, documentos, usuários e credenciais de outros ambientes
não fazem parte desta versão.

## Segurança essencial

- `DEBUG=False`;
- banco obrigatório por `DATABASE_URL`;
- bloqueio de hosts e nomes associados a ambientes não demonstrativos;
- cookies seguros em HTTPS;
- CSRF, autenticação, autorização, rate limiting e auditoria preservados;
- cadastro público e uploads desabilitados;
- uma única conta administrativa inicial, criada por variáveis de ambiente.

## Workflow conectado com IA e MCP

A Sprint 17 demonstra o conteúdo do curso com um fluxo controlado:

1. o agente consulta somente a API autorizada;
2. o adaptador MCP oferece ferramentas específicas;
3. a IA cria uma proposta na forma de rascunho;
4. o rascunho permanece **não executado**;
5. uma pessoa autenticada confere contexto, comparação e evidências;
6. a pessoa aprova ou rejeita;
7. somente após aprovação o backend revalida e executa o serviço oficial;
8. o resultado fica registrado na auditoria.

O MCP nunca acessa diretamente o banco, não confirma propostas e não possui
ferramentas para homologar, atestar ou autorizar pagamentos.

### Configuração local do MCP

A configuração versionada está em `.mcp.json` e não contém credenciais.
O token demonstrativo deve ser fornecido somente pelo ambiente:

```sh
export FISCALSEMA_API_URL=http://127.0.0.1:8000
export FISCALSEMA_API_TOKEN=<credencial-demonstrativa>
python scripts/mcp_server.py
```

Nunca salve o valor real do token no Git, em captura de tela ou documentação.

### Teste isolado

```sh
python -m unittest scripts.test_mcp_server
```

O escopo, a matriz de autonomia e o roteiro de apresentação estão em
`docs/sprints/sprint-17-workflow-ia-mcp/`.

Leia `docs/README.md` antes de qualquer publicação. As mudanças são registradas
por sprint, sem misturar o código executável com a documentação de evolução.
