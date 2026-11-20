# Testes — Sprint 60

## Critérios automatizados (`assistant/test_dados_por_perfil.py`)

- Auxiliar, com ou sem contrato selecionado, não recebe `financeiro`,
  `empenhado`, `pago`, `saldo_contratual`, `valor_atual`, itens, regras,
  achados nem o nome da contratada;
- Auxiliar recebe a OS aberta em atraso, com prazo, valor unitário e valor da
  OS em reais, e o total das OS abertas;
- Auxiliar não alcança contrato arquivado nem um ID inexistente;
- com 61 OS abertas, o bloco continua sendo um JSON válido dentro do limite e
  avisa que a lista foi reduzida;
- Fiscal Titular e Gestor do Contrato continuam recebendo o snapshot com
  `financeiro`, itens e OS, agora com os valores em reais;
- Gestor Administrativo continua recebendo a carteira consolidada e, com um
  contrato selecionado, o snapshot financeiro;
- `reais` formata 22400 como "R$ 22.400,00", arredonda centavos, trata
  negativos e mantém valores não numéricos.

## Execução

Ver a seção "Registro da execução" abaixo.

## Registro da execução

Data: 20/11/2026.

- `python scripts/security/scan_repository.py` — aprovado (PASS, código 0);
- `python -m unittest scripts.test_mcp_server` — 6 testes aprovados;
- compilação de `assistant/ferramentas.py` e do teste novo — aprovada;
- `git diff --check` — aprovado;
- conferência isolada da função `reais` (22400 → "R$ 22.400,00",
  arredondamento, negativo e valores não numéricos) — aprovada;
- dependências instaladas no contêiner descartável com
  `pip install -r requirements.txt` (versões fixadas, arquivo sem alteração),
  com autorização do responsável;
- PostgreSQL 16 local e temporário, com credenciais fictícias iguais às da CI,
  removido ao final;
- `python manage.py makemigrations --check --dry-run` — "No changes detected";
- `python manage.py check --settings=core.settings_test` — sem alertas;
- `python manage.py test assistant.test_dados_por_perfil` — 7 testes
  aprovados;
- prova de cobertura: os mesmos testes rodados contra o `ferramentas.py`
  anterior falharam (6 falhas e 1 erro), confirmando que detectam a exposição
  de valores à Auxiliar;
- `python manage.py test --settings=core.settings_test --noinput` — **756
  testes aprovados** (OK, código 0), em 74,9 s.

Nenhum banco real ou de produção foi acessado.

## Publicação e validação em produção

Data: 20/11/2026.

- CI do Pull Request `#60` (GitHub Actions `44801368344`, job
  `django-postgresql`) — aprovada antes do merge;
- Pull Request `#60` incorporado à `main` por rebase no commit `8dae457`,
  com autorização do responsável;
- GitHub Actions da `main`, execução `44802076480`, job `django-postgresql`
  — aprovado (migrations e configuração, configuração Vercel sem banco,
  auditoria de segredos, adaptador MCP e testes integrais);
- Vercel concluiu o deploy de produção do commit `8dae457` (estado `READY`);
- `https://fiscalsema-demo.vercel.app/healthz` respondeu HTTP `200` com
  aplicação e banco de dados em estado `ok`;
- pendente: repetir no perfil Auxiliar a pergunta "Qual é o saldo e o valor
  pago do contrato DEMO-0002-01/2026?" e confirmar que o Arise informa que
  esses dados não estão autorizados. A senha da demonstração não foi acessada.

Nenhum banco real ou de produção foi acessado diretamente.
