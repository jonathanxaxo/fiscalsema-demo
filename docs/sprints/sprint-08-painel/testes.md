# Testes e evidências da Sprint 08

| Verificação | Comando | Resultado |
|---|---|---|
| Conteúdo preservado | `diff` das linhas ordenadas de `home.html` antes/depois | única diferença: 3 linhas da barra de atalhos |
| Testes novos | `core.test_painel_ordem` | 2 aprovados |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **424 aprovados** |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Ordem no navegador | Playwright, títulos `h2` na ordem de exibição | Central de trabalho → Prazos de OS → NF pendentes → NF que exigem atenção → Como está meu contrato? → ... → Fechamento e ano do contrato |
| Atalho "Empenhos" | Playwright, clique na barra (computador e iPhone 13) | rótulo e título da seção visíveis abaixo da barra |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |

Capturas: `capturas/01-painel-antes.png`, `02-painel-depois.png`,
`03-atalho-empenhos.png`.
