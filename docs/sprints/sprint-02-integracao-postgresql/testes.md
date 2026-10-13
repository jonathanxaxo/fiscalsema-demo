# Testes da Sprint 02

## Resultado final

| Verificação | Resultado |
|---|---|
| Projeto original | Preservado e não alterado |
| Repositório da demo | Privado e sincronizado com a branch `main` |
| Banco de validação | PostgreSQL 17 descartável e exclusivo do GitHub Actions |
| Migrações | `makemigrations --check --dry-run` aprovado |
| Configuração Django | `check` aprovado |
| Configuração Vercel | `check --deploy` e `collectstatic` aprovados sem acessar banco operacional |
| Auditoria do repositório | Nenhum segredo conhecido, dado real ou artefato proibido encontrado |
| Suíte integral | **408 testes aprovados** em 59,850 segundos |
| Banco original/VM | Não acessado |
| Commit validado | `254c8d43293cbb70e917e074276067562a5c4b91` |
| Execução | GitHub Actions nº `38395479419` |

## Correções comprovadas pela primeira execução

A primeira execução encontrou dois testes herdados que ainda verificavam
características exclusivas da VM:

1. o texto visual `Ambiente interno`, substituído na demo pelo aviso explícito
   `AMBIENTE DE DEMONSTRAÇÃO — DADOS EXCLUSIVAMENTE FICTÍCIOS`;
2. arquivos do Nginx, que não pertencem à arquitetura serverless da Vercel.

Os testes foram adaptados para validar os controles equivalentes da demo:

- identificação inequívoca do ambiente fictício;
- arquivos estáticos versionados pelo WhiteNoise;
- roteamento da função Django no `vercel.json`;
- cabeçalhos `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e
  `Permissions-Policy` na borda da Vercel.

Nenhuma funcionalidade, dado ou configuração da VM foi alterada.

## Observação operacional

O Docker Desktop local não foi necessário. O teste integral foi realizado no
GitHub Actions com um PostgreSQL temporário, removido automaticamente ao fim da
execução.
