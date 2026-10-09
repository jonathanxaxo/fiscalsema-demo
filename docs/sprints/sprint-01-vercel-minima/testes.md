# Testes da Sprint 01

## Resultado local em 9 de outubro de 2026

| Verificação | Resultado | Evidência resumida |
|---|---|---|
| Instalação das dependências | Aprovado | Ambiente virtual isolado e `pip check` sem incompatibilidades |
| Compilação Python | Aprovado | `python -m compileall -q .` sem erro |
| Configuração Django | Aprovado | `manage.py check` sem problema |
| Migrações | Aprovado com limitação | Nenhuma migração nova detectada; a consulta ao histórico não ocorreu porque o endereço usado no teste era propositalmente inexistente |
| Arquivos estáticos | Aprovado | 131 arquivos coletados, comprimidos e registrados no manifesto WhiteNoise |
| Proteção contra banco local/real | Aprovado | URLs locais e conexões sem `sslmode` foram recusadas pelo settings demo |
| Interface de demonstração | Aprovado | Login respondeu 200, aviso de dados fictícios visível e cadastro público indisponível |
| Headers básicos | Aprovado | `X-Frame-Options: DENY` e `X-Content-Type-Options: nosniff` confirmados |
| Auditoria do repositório | Aprovado | Scanner não encontrou segredo, dado real ou arquivo operacional versionado |
| Testes completos com PostgreSQL | Pendente | Exigem banco PostgreSQL exclusivo da demo; o banco e a VM originais não foram usados |

## Avisos deliberados

O `check --deploy` manteve `SECURE_HSTS_INCLUDE_SUBDOMAINS=False` e
`SECURE_HSTS_PRELOAD=False`. Essa escolha evita impor HSTS a subdomínios de
terceiros no domínio compartilhado `vercel.app`. Esses controles só devem ser
ativados depois de configurar e validar um domínio próprio.

## Limite desta sprint

Não houve commit, push, criação de repositório remoto, provisionamento de banco
ou deploy. O teste integral será executado somente com um PostgreSQL demo
isolado e autorizado.
