# Deploy na Vercel

## Pré-requisitos

1. Repositório Git separado e sem histórico do `fiscalsema-light`.
2. PostgreSQL novo, vazio e exclusivo da demo, com TLS e pooler serverless.
3. Usuários PostgreSQL separados para migrations e execução.

## Variáveis obrigatórias

- `APP_ENVIRONMENT=demo`
- `DJANGO_SETTINGS_MODULE=core.settings_demo`
- `DJANGO_SECRET_KEY`
- `FISCALSEMA_DEMO_DATABASE_URL` (conexão exclusiva usada pela aplicação)
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

Quando `FISCALSEMA_DEMO_DATABASE_URL` estiver definida, ela substitui a
`DATABASE_URL` genérica fornecida pela integração da plataforma. O nome do
banco e o usuário da conexão efetiva precisam conter `demo`. A configuração
recusa hosts locais, o IP conhecido da VM e o hostname Docker.

## Preparação do banco

Execute migrations uma única vez usando a credencial de migration. Não execute
migrations durante cada requisição da Vercel. Depois, configure
`FISCALSEMA_DEMO_DATABASE_URL` com o usuário de runtime, que não deve criar
banco, schema ou roles.

O fluxo manual fica em `.github/workflows/migrate-demo.yml`. A credencial do
proprietário das tabelas deve existir somente no secret
`FISCALSEMA_DEMO_MIGRATION_DATABASE_URL` do GitHub. Ao final, o fluxo executa
`scripts/deploy/grant_demo_runtime.py`, que concede ao usuário web apenas
conexão, uso do schema e operações usuais nas tabelas e sequências.

## Publicação

A Vercel detecta o `manage.py` e o WSGI do Django, executa `collectstatic` no
build e encaminha as rotas públicas diretamente para a aplicação. Não deve
existir uma reescrita global para `/api/index`, pois isso troca o caminho que o
Django recebe e causa resposta 404. Não há Gunicorn, Nginx, Docker ou volume
persistente.

Push e deploy somente devem ocorrer após auditoria de segredos e autorização.
