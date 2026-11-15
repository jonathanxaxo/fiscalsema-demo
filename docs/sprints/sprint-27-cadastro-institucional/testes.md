# Testes e evidências da Sprint 27

| Verificação | Comando | Resultado |
|---|---|---|
| Cadastro institucional | `python manage.py test accounts.test_cadastro_institucional --settings=core.settings_test --noinput` | 13 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **559 aprovados** |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

Cobertura (domínios fictícios, Google simulado): regras da política; lista
vazia bloqueia todos; `hd` exigido quando ligado (exceção individual não
depende de Workspace); formulário com senha aplica a política; novo usuário
institucional fica pendente, sem senha, sem organização, com vínculo Google e
auditoria; exceção do professor exata (colega do mesmo domínio recusado; sem
acesso administrativo); e-mail pessoal recusado; e-mail não verificado nunca
chega ao cadastro; domínio sem prova de Workspace recusado quando exigido;
duplicidade evitada; sessão do cadastro expira; pendente não entra e, após
aprovação, entra pelo Google; contas existentes ignoram a política.
