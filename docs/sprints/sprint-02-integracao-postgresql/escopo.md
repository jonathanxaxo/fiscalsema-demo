# Escopo da Sprint 02

## Objetivo

Consolidar a primeira versão do repositório local e validar migrações e testes
integrais com um PostgreSQL 17 exclusivo e descartável.

## Limites

- não acessar o PostgreSQL da VM;
- não acessar o PostgreSQL 9.6 já instalado no Windows;
- não copiar dados, usuários ou documentos reais;
- manter o repositório GitHub privado;
- não publicar na Vercel sem nova autorização;
- não criar recurso externo ou pago sem nova autorização.

## Estado

A sprint foi concluída no repositório privado. A suíte integral foi executada
no GitHub Actions com PostgreSQL 17 temporário, sem depender do Docker Desktop
local e sem acessar a VM.
