# Testes e evidências da Sprint 23

| Verificação | Comando | Resultado |
|---|---|---|
| Assistente + Metodologia | `python manage.py test assistant core.test_metodologia --settings=core.settings_test --noinput` | 44 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **518 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

## Navegador (servidor local + provedor falso local)

| Verificação | Computador | Celular (iPhone 13) |
|---|---|---|
| Ícone no login | não aparece | não aparece |
| Painel abre pelo ícone | sim | sim (tela inteira) |
| Resposta com lista e tabela | sim | sim |
| Fecha com Esc | sim | sim |
| Conversa continua em outra tela | 2 mensagens | 2 mensagens |
| Nova conversa limpa o painel | sim | sim |
| Ícone na tela cheia do assistente | não aparece | não aparece |
| Rolagem lateral | não | não |
