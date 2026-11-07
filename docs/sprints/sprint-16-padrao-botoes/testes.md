# Testes e evidências da Sprint 16

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte após as mudanças | `python manage.py test --settings=core.settings_test --noinput` | 456 aprovados |
| Testes novos do padrão | `core.test_padrao_botoes` | 4 aprovados |
| Suíte integral final | mesmo comando | **460 aprovados** |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

## Medição no navegador (altura/fonte de todos os botões visíveis)

| Tela | Antes | Depois |
|---|---|---|
| Relatório | 37 px/13,3 e 42 px/16 | 40 px/14,4 |
| Prestação de contas | 46 px + links "·" | 40 px |
| Modo tabela | abas próprias + 46 px | 40 px |
| Contrato | 46 px e 35 px | 40 px e 34 px |
| OS / NF | 46 px + links | 40 px |
| Usuários / Organizações | 46, 39 e 34 px | 40 px e 34 px |
| Solicitações | links "·" | 40 px |

Impressão do relatório: nova aba, impressão automática, PDF sem topo, menu ou
botões.
