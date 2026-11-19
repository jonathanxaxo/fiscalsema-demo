# Testes — Sprint 57

## Executados localmente

- `python -m compileall -q accounts contracts` — sintaxe aprovada;
- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- `python scripts/security/scan_repository.py` — nenhum segredo, dado real ou
  artefato proibido encontrado;
- `git diff --check` — aprovado.

## Preparados para a CI

- troca direta entre os cinco perfis e retorno à conta controladora;
- recusa de outras contas e de sessão adulterada;
- senha da controladora preservada e contas internas sem senha utilizável;
- contas internas ocultas da gestão comum;
- evento de auditoria em cada troca;
- carga fictícia classificada e idempotente;
- visibilidade integral ou individual conforme cada perfil;
- compatibilidade com a troca Fiscal/Administrador existente;
- checagem de migrations, Django, segurança, MCP e suíte integral.

O ambiente Python local não contém o Django instalado. Nenhuma dependência foi
instalada sem autorização; a suíte PostgreSQL foi executada pela CI do PR.

## CI do Pull Request

- PR `#53`;
- GitHub Actions `44588237203` — aprovado;
- migrations e configuração Django — aprovadas, sem alterações ausentes;
- configuração Vercel sem acesso ao banco — aprovada;
- varredura de segurança — aprovada;
- adaptador MCP — 6 testes aprovados;
- suíte Django em PostgreSQL 17 — **743 testes aprovados**.

O status automático de Preview da Vercel foi recusado antes da construção
porque o autor Git do commit não pertence à equipe configurada na Vercel. Isso
não é falha de teste ou de código; a correção do vínculo e qualquer Preview
permanecem para a etapa de publicação autorizada.

## Publicação

PENDENTE — esta Sprint está autorizada somente para implementação e abertura de
PR. Preview, merge, migration, preparação do banco e produção exigem a etapa de
publicação autorizada.
