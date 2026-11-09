# Sprint 17 — Workflow conectado com IA e MCP

## Objetivo

Demonstrar, com dados exclusivamente fictícios, o fluxo ensinado no curso:

API autorizada → ferramenta MCP → proposta da IA não executada → revisão humana
→ confirmação ou rejeição → serviço oficial → auditoria.

## Incluído

- adaptador MCP que consome somente a API HTTP;
- consultas limitadas ao escopo da credencial;
- ferramenta para criar apenas rascunhos controlados;
- identificação explícita de `executada: false`;
- revisão visual antes/depois e evidências;
- matriz de autonomia, arquitetura e roteiro de apresentação;
- testes unitários do limite de confiança MCP.

## Fora do escopo

- acesso direto ao banco pelo agente;
- aprovação ou execução pelo MCP;
- uso de dados reais;
- criação automática de credenciais;
- alteração de regras financeiras;
- migrations;
- deploy, merge ou publicação sem nova autorização.

## Critérios de aceite

1. Nenhuma ferramenta MCP confirma ou executa rascunhos.
2. Consultas usam a API e respeitam a credencial.
3. A proposta retorna `executada: false` e exige aprovação humana.
4. Segredos não são versionados.
5. Testes do adaptador comprovam os limites.
6. A interface identifica claramente o estado não executado.
