# Sprint 54 — Perfis funcionais e autorização

## Objetivo

Substituir os perfis genéricos pelos cinco papéis funcionais confirmados para a
demonstração e aplicar suas restrições no backend, sem ampliar permissões por
atalhos de interface.

## Entregas

- Administrador Geral com criação de contas, alteração auditada de perfil,
  bloqueio, ativação, arquivamento e restauração de usuários;
- Fiscal Titular com a operação contratual já existente;
- Auxiliar Administrativa com acesso aos contratos ativos, somente aos
  metadados administrativos dos documentos e sem acesso a contratos arquivados;
- Gestor Administrativo com leitura da carteira institucional ativa e emissão
  de relatórios;
- Gestor do Contrato com leitura, painéis e relatórios apenas dos contratos
  individualmente vinculados;
- remoção de Usuário de Consulta das escolhas novas, preservando contas
  legadas para reclassificação explícita pelo Administrador;
- cadastro público com perfil solicitado e justificativa, sempre sujeito à
  aprovação administrativa.

## Fora do escopo

- migração silenciosa de contas legadas;
- acesso a contratos arquivados pela Auxiliar;
- leitura do arquivo privado pela Auxiliar;
- publicação, push ou deploy.
