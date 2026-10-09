# Deploy na Vercel

## Pré-requisitos

1. Repositório Git separado e sem histórico do `fiscalsema-light`.
2. PostgreSQL novo, vazio e exclusivo da demo, com TLS e pooler serverless.
3. Usuários PostgreSQL separados para migrations e execução.

## Variáveis obrigatórias

- `APP_ENVIRONMENT=demo`
- `DJANGO_SETTINGS_MODULE=core.settings_demo`
- `DJANGO_SECRET_KEY`
- `DATABASE_URL`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

O nome do banco e o usuário da `DATABASE_URL` precisam conter `demo`. A
configuração recusa hosts locais, o IP conhecido da VM e o hostname Docker.

## Preparação do banco

Execute migrations uma única vez usando a credencial de migration. Não execute
migrations durante cada requisição da Vercel. Depois, configure `DATABASE_URL`
com o usuário de runtime, que não deve criar banco, schema ou roles.

## Publicação

A Vercel executa `collectstatic` no build e encaminha as rotas para
`api/index.py`. Não há Gunicorn, Nginx, Docker ou volume persistente.

Push e deploy somente devem ocorrer após auditoria de segredos e autorização.
