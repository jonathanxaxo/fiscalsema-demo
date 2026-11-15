# Testes — Sprint 43

Novos testes em `contracts/test_nf_botao_catalogo.py`:
1. seção de NF com botão e aviso de homologação;
2. serviço homologado com link que abre a NF com o serviço marcado;
3. formulário explica lista vazia;
4. parâmetro inválido ou de outro serviço é ignorado.

Resultados registrados abaixo após a execução da suíte completa.

| Comando | Resultado |
|---|---|
| `python scripts/security/scan_repository.py` | PASS |
| `python -m unittest scripts.test_mcp_server` | OK |
| `python manage.py makemigrations --check --dry-run` | No changes detected |
| `python manage.py test --settings=core.settings_test --noinput` | **677 testes OK** |
