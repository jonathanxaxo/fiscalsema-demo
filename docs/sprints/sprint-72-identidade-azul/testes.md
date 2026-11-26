# Testes — Sprint 72

## Critérios automatizados (`core/test_identidade_azul.py`)

- paleta azul do prompt mestre aplicada às variáveis do CSS e nenhum verde
  antigo em `app.css` e `chat.css`;
- cores de sucesso, perigo e atenção preservadas;
- cor do tema `#083b8a`;
- logotipo animado, estático e favicon com documento, lupa e verificação em
  azul e branco; escaneamento só na versão animada;
- imagem institucional em 1698 × 543 px, RGBA (fundo transparente), exibida
  com altura automática (sem recorte);
- login com a imagem abaixo do formulário, login Google e recuperação de
  senha preservados;
- rodapé institucional em Painel, Contratos e Metodologia, oculto na
  impressão;
- ausência da faixa e das notas de demonstração; selo de perfil em azul claro.

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
Ran 823 tests — OK

git diff --check
sem problemas
```

## Conferência visual

Servidor local com banco fictício, versão anterior (`main`) e nova, em
1440 × 900, 1366 × 768 e 390 × 844: login, painel do contrato (Fiscal
Titular) e lista de contratos. Capturas em `capturas/`.

## Publicação

- PR #71: CI `django-postgresql` aprovada; Preview conferido; merge em
  26/11/2026 (commit `e2aced7`) após aprovação do responsável.
- Sem migration; nenhuma execução do fluxo de migração foi necessária.
- Vercel: deploy de produção `READY` para o commit `e2aced7`.
- Conferência em produção: `/healthz` com banco "ok", nenhum erro de execução
  em 15 minutos e login com identidade azul, logotipo novo e imagem
  institucional, sem a faixa de demonstração.
