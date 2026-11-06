# Testes e evidências da Sprint 07

| Verificação | Comando | Resultado |
|---|---|---|
| Suíte após as mudanças, antes dos testes novos | `python manage.py test --settings=core.settings_test --noinput` | 416 aprovados |
| Testes novos | `python manage.py test core.test_padronizacao_telas --settings=core.settings_test` | 6 aprovados |
| Suíte integral final | mesmo comando | **422 aprovados** |
| Configuração | `python manage.py check --settings=core.settings_test` | sem problemas |
| Migrations | `python manage.py makemigrations --check --dry-run` | nenhuma alteração |
| Auditoria | `python scripts/security/scan_repository.py` | `PASS` |
| Navegador (Playwright) | OS, itens, empenhos, contrato, formulário, rascunhos | todas HTTP 200; 5 capturas em `capturas/` |
| Menu no celular | iPhone 13, menu aberto | começa abaixo do cabeçalho (`capturas/menu-celular.png`) |
