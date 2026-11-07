# Testes e evidências da Sprint 15

| Verificação | Comando | Resultado |
|---|---|---|
| Teste novo do botão e da versão de impressão | `contracts.test_reports` | 12 aprovados (1 novo) |
| Suíte integral | `python manage.py test --settings=core.settings_test --noinput` | **456 aprovados** |
| Configuração / migrations / auditoria | `check`, `makemigrations --check`, `scan_repository.py` | sem problemas / nenhuma / `PASS` |

## Navegador (Playwright, contrato fictício 000885/2026)

| Verificação | Resultado |
|---|---|
| Clique em "Imprimir / Salvar PDF" abre nova aba com `print=1` | sim |
| Janela de impressão chamada automaticamente | sim |
| PDF gerado com o CSS de impressão | paisagem, 2 páginas |
| Instrução de tela no papel (1ª geração) | **sim — corrigido** |
| Instrução de tela no papel (após correção) | não |
