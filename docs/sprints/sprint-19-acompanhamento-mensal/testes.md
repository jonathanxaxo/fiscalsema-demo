# Testes e evidências da Sprint 19

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test contracts.test_acompanhamento_mensal --settings=core.settings_test --noinput` | 10 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **474 aprovados** |
| Adaptador MCP | `python -m unittest scripts.test_mcp_server` | OK |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma pendente (0020 criada nesta sprint) |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

## O que os testes novos cobrem

- campo desmarcado por padrão; OS não marcada fica fora;
- OS marcada sem registros no mês: vermelho "pendente";
- execução → NF → pagamento do mês mudam a situação até o verde;
- registros de outro mês não contam;
- item com unidade Mês entra sozinho;
- suspensa fica amarela; concluída sai da lista;
- marcação registrada na auditoria (anterior/atual);
- formulário com a caixinha; painel, lista ("Mensal") e detalhe;
- sino com aviso vermelho e link para a OS.

## Conferência visual (servidor local, dados fictícios)

`capturas/1-painel-desktop.png`, `1-painel-celular.png`, `2-sino.png`,
`3-lista-os.png`, `4-detalhe-os.png`, `5-formulario-os.png`.

## Produção

Pendente: após o merge, executar `migrate-demo.yml` e marcar uma OS na tela.
