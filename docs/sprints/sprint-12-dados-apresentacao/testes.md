# Testes e evidências da Sprint 12

| Verificação | Comando | Resultado |
|---|---|---|
| Testes novos | `python manage.py test contracts.test_seed_demo_presentation --settings=core.settings_test` | **5 aprovados** |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **445 aprovados** (440 + 5) |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

Casos testados: pacote completo criado dentro dos limites do contrato
(3 itens, 2 empenhos, 5 OS nas situações previstas, 2 execuções, 2 NFs,
1 pagamento, saldo positivo); repetição sem efeito; painel do Fiscal mostra a
OS vencida; recusa de contrato de outro Fiscal; recusa fora do ambiente demo.

## Produção

PENDENTE — merge e execução do fluxo, mediante autorização.
