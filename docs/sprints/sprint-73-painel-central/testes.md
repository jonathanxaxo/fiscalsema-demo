# Testes — Sprint 73

## Critérios automatizados (`core/test_painel_sprint73.py`)

- explicação curta em cada indicador e no comprometido e faturado;
- bloco de definições coerente com o motor financeiro;
- saldo exibido = valor atual − comprometido (fórmula inalterada);
- resumo e rótulos de urgência com os critérios existentes, com "Urgente"
  antes de "Atenção";
- atalhos para Notas e pagamentos, Arise com o contrato e Auditoria somente
  com permissão;
- dashboard individual com a mesma regra de auditoria.

O teste já existente da Central de trabalho (`core/test_painel_ordem.py`)
detectou durante a sprint uma tag `</strong>` removida por engano na linha da
OS vencida; a falha foi corrigida antes da entrega.

## Comandos e resultados (26/11/2026)

```text
python scripts/security/scan_repository.py
PASS | nenhum segredo conhecido, dado real ou artefato proibido encontrado

python -m unittest scripts.test_mcp_server
Ran 6 tests — OK

python manage.py check --settings=core.settings_test
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run --settings=core.settings_test
No changes detected

python manage.py test --settings=core.settings_test --noinput --parallel 4
Ran 829 tests — OK

git diff --check
sem problemas
```

## Conferência visual

Servidor local com banco fictício, versão anterior (`main`) e nova, em 1440,
1366 e 390 px, perfil Fiscal Titular: atalhos, indicadores e Central de
trabalho. Capturas em `capturas/`.
