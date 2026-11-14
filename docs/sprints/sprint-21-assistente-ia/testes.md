# Testes e evidências da Sprint 21

| Verificação | Comando | Resultado |
|---|---|---|
| Cliente de IA | `python manage.py test assistant.test_provedor --settings=core.settings_test --noinput` | 11 aprovados |
| Assistente (telas, conversas, limites, auditoria, prompt) | `python manage.py test assistant --settings=core.settings_test --noinput` | 33 aprovados (inclui os 11 acima) |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **512 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma pendente (`assistant/0001_conversas` criada nesta sprint) |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

Nenhum teste acessa a internet: o provedor é simulado.

## Cobertura

- recuo do nível de raciocínio em 400 e memória do nível por modelo;
- troca de modelo em 403/404/429/5xx/tempo esgotado; parada em 401;
- texto em streaming não é cortado; chave nunca aparece em log ou mensagem;
- anônimo → login; CSRF exigido; menu oculto sem chave ou desativado;
- conversa salva só para o dono; outro usuário recebe 404 (ver, perguntar, excluir);
- retenção de 30 dias; exclusão da conversa;
- limite por minuto e por dia (por usuário); falha do provedor → mensagem em
  português e nada gravado; resposta interrompida avisa o usuário;
- auditoria só com metadados (sem pergunta nem resposta); rótulo na auditoria global;
- seções da ajuda respeitam o perfil; blocos delimitados; histórico limitado;
- Metodologia lista a sprint mais recente.

## Conferência no navegador (servidor local + provedor falso local, sem chave real)

| | Computador (1366 px) | Celular (iPhone 13) |
|---|---|---|
| Item "Assistente IA" no menu | sim | sim |
| 1ª lista da resposta visível (provedor falso com 0,4 s de espera) | 0,86 s | 0,86 s |
| Tabela formatada | sim | sim |
| Conversa recuperada após recarregar | 4 mensagens | 4 mensagens |
| Rolagem lateral | não | não |
| Limite por minuto | 429 com mensagem em português ao exceder 6/min | — |

## Pendente (depende da publicação autorizada)

- medição com o Gemini real no Preview (10 perguntas; meta: 1ª palavra ≤ 2 s);
- confirmar se a função Python da Vercel entrega o texto em partes;
- teste no site publicado com os três perfis.
