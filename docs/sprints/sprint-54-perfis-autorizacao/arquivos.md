# Arquivos — Sprint 54

| Grupo | Alteração |
|---|---|
| `accounts/` | Perfis, grupos, formulários, serviços administrativos, auditoria e migrações `0010`/`0011` |
| `accounts/management/commands/inventory_functional_profiles.py` | Inventário somente leitura dos perfis e das contas legadas |
| `contracts/services.py` e `contracts/models.py` | Visibilidade, escrita, exportação e vínculo do Gestor do Contrato |
| `contracts/migrations/0024_contract_manager_access.py` | Preservação do tipo único `READ_ONLY` para vínculos individuais |
| `documents/services.py` e `documents/views.py` | Separação entre metadados e conteúdo privado |
| `api_v1/views.py`, `api_v1/mcp_remoto.py` e `api_v1/test_functional_profiles.py` | Mesma autorização na API/MCP, com metadados sem conteúdo para a Auxiliar |
| `templates/accounts/`, `templates/contracts/` e `templates/documents/` | Controles e avisos coerentes com o backend |
| `accounts/test_functional_profiles.py` e testes existentes | Cobertura dos perfis atuais e compatibilidade dos fluxos |

Nenhum arquivo foi removido.
