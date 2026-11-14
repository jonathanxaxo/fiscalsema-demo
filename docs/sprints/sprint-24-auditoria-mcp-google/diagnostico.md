# Diagnóstico — contas, API, MCP, rascunhos e cadastros (Sprint 24)

## 1. Contas, perfis e vínculos

| Elemento | Situação atual | Arquivo |
|---|---|---|
| Usuário | `accounts.User` customizado, login por e-mail normalizado (`normalize_login_email`: minúsculas), campos de organização/setor informados e vinculados | `accounts/models.py`, `managers.py` |
| Situação da conta | `PENDENTE_DE_APROVACAO`, `ATIVO`, `INATIVO`, `BLOQUEADO`, `REJEITADO`; exclusão lógica (`archived_at`) | `accounts/models.py` |
| Perfis | `ADMINISTRADOR`, `FISCAL`, `USUARIO_CONSULTA`, espelhados em grupos de permissão | `accounts/constants.py`, `signals.py` |
| Autenticação | `AccountStatusBackend`: só entra quem está ativo e com status `ATIVO`; bloqueio por tentativas (`LoginThrottle`); troca de senha obrigatória por middleware | `accounts/backends.py`, `middleware.py` |
| Cadastro | `FiscalRegistrationView` + `RegistrationRequest` (aprovação pelo Administrador); **desligado na demo** (`PUBLIC_REGISTRATION_ENABLED=False`) | `accounts/views.py`, `core/settings_demo.py` |
| Criação pelo Administrador | `AdministrativeFiscalCreateView` ("Criar Fiscal") | `accounts/views.py` |
| Recuperação de senha | Fluxo padrão do Django; **e-mail fictício na demo** (nenhuma mensagem é enviada) | `accounts/views.py`, `core/settings_base.py` |
| Troca de perfil | Exceção da demo: `ProfileSwitchLink` entre duas contas, auditada | `accounts/profile_switch.py` |
| "Minha Conta" | **Não existe** página própria; só "Alterar senha" | — |
| Login externo (Google) | **Não existe** | — |

## 2. Contratos e permissões

- Contrato pertence a uma organização contratante e a um **Fiscal responsável**.
- Acesso adicional: `ContractAccess` (somente leitura) e `FiscalSubstitution` (substituto).
- Funções oficiais de escopo: `contracts_visible_to(user)` (leitura) e
  `contracts_writable_by(user)` (escrita: só Fiscal ativo, de organização ativa).
- Administrador **não** opera contratos (grupo sem `view_all_contracts`).

## 3. API v1 e credenciais

- Endpoints somente leitura por contrato: lista, detalhe, resumo, itens, empenhos,
  OS, rateios, execuções, NF, pagamentos, documentos, resumo financeiro,
  prestação de contas, relatório, conferência de NF, conteúdo de documento.
- `ApiCredential`: token individual guardado em **hash**, ligado a um usuário
  autorizador, modo `READ_ONLY` ou `CONTROLLED_DRAFT`, expiração, revogação,
  limite por minuto (`API_RATE_LIMIT_PER_MINUTE`).
- Criada e revogada por **comando de administrador**
  (`create_api_credential`, `revoke_api_credential`) — não há tela para o usuário.
- A cada requisição: token, revogação, expiração e conta ativa são conferidos
  (`api_v1/services.py: authenticate_token`).
- Auditoria: `ApiAccessEvent` (consulta autorizada/negada).

## 4. MCP atual

- `scripts/mcp_server.py`: servidor **local (stdio)**, protocolo `2025-06-18`,
  sem Django e sem banco; usa só a API HTTP com `FISCALSEMA_API_TOKEN`.
- 8 ferramentas: `listar_contratos_autorizados`, `consultar_resumo_contrato`,
  `consultar_itens`, `consultar_empenhos`, `consultar_ordens_servico`,
  `consultar_notas_fiscais`, `consultar_pendencias`, `propor_rascunho`.
- **Não há MCP remoto** (HTTP) nem OAuth: cada pessoa precisaria de um token
  criado pelo administrador e configurado manualmente no cliente.

## 5. Rascunhos e confirmação humana (Sprint 17)

- `AssistantDraft`: payload, evidências, comparação, autoridade da fonte,
  nível de confiança, `baseline_hash` do estado comparado, lote, status.
- Confirmação **somente pelo usuário autorizador**, pela tela do FiscalSema;
  revalida pelo mesmo formulário da interface; recusa se o registro mudou
  (`baseline_hash`); grava pelos serviços oficiais; audita
  (`AssistantDraftEvent`, inclusive falhas de validação).
- **Lacunas para a execução pelo chat externo:** não há prazo de validade,
  chave de idempotência, código de confirmação de uso único nem ligação com
  a conexão (cliente) que criou a proposta.

## 6. Ambiente demo (Vercel)

- Função Python (WSGI) sem estado, região `gru1`, PostgreSQL exclusivo,
  segredos só em variáveis da Vercel, uploads desligados, e-mail fictício.
- Auditoria **imutável** no banco (gatilhos impedem alterar eventos).
- Implicação: MCP remoto deve ser **sem estado** (JSON por requisição) e
  tokens/propostas ficam no PostgreSQL.

## 7. Testes existentes relevantes

- `accounts/tests.py` (38), `api_v1/tests.py` (20),
  `api_v1/test_operational_ai.py` (12), `scripts/test_mcp_server.py` (6),
  além da suíte completa (518 testes na Sprint 23).

## 8. Verificações externas

| Verificação | Resultado |
|---|---|
| O domínio institucional da SEMA usa Google Workspace? | **Pendente.** A rede desta sessão bloqueia consulta de DNS. O responsável pode verificar os registros MX do domínio em uma ferramenta pública de consulta de DNS: servidores `*.google.com`/`*.googlemail.com` indicam Google Workspace. |
| `django-oauth-toolkit` 3.4.1 | Compatível com Django 4.2–6.0 e Python 3.10–3.14 (classificadores do PyPI, publicado em 21/08/2026). **Dependências transitivas:** `requests`, `urllib3`, `oauthlib`, `jwcrypto` (que usa `cryptography`, com partes compiladas). Licença BSD. |
